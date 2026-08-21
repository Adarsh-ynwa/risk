"""Application services for transactions, risk, and analytics."""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.db_models import ActionLog, Investigation, RiskAssessment, Transaction
from app.schemas.schemas import (
    ActionResponse,
    CustomerProfile,
    InvestigationReport,
    InvestigationResponse,
    ModelMetrics,
    PaginatedTransactions,
    RiskAnalyzeResponse,
    RiskSummary,
    StatsResponse,
    ToolCallRecord,
    TransactionDetail,
    TransactionSummary,
    TriggeredRule,
)
from app.services.ml_service import ml_service
from app.services.risk_engine import compute_risk


def transaction_to_dict(txn: Transaction) -> dict[str, Any]:
    return {
        "transaction_id": txn.transaction_id,
        "customer_id": txn.customer_id,
        "transaction_date": txn.transaction_date,
        "transaction_time": txn.transaction_time,
        "hour_of_day": txn.hour_of_day,
        "is_weekend": txn.is_weekend,
        "is_night_transaction": txn.is_night_transaction,
        "country": txn.country,
        "city": txn.city,
        "merchant_category": txn.merchant_category,
        "payment_method": txn.payment_method,
        "device_type": txn.device_type,
        "customer_age": txn.customer_age,
        "credit_score": txn.credit_score,
        "account_age_years": txn.account_age_years,
        "account_balance": txn.account_balance,
        "transaction_amount": txn.transaction_amount,
        "num_prev_transactions": txn.num_prev_transactions,
        "transaction_freq_monthly": txn.transaction_freq_monthly,
        "distance_from_home_km": txn.distance_from_home_km,
        "time_since_last_txn_hrs": txn.time_since_last_txn_hrs,
        "is_international": txn.is_international,
        "failed_attempts": txn.failed_attempts,
        "pin_changed_recently": txn.pin_changed_recently,
        "is_fraud": txn.is_fraud,
        "risk_score": txn.risk_score,
        "risk_level": txn.risk_level,
        "status": txn.status,
        "action": txn.action,
    }


def get_latest_assessment(db: Session, transaction_id: str) -> RiskAssessment | None:
    return (
        db.query(RiskAssessment)
        .filter(RiskAssessment.transaction_id == transaction_id)
        .order_by(desc(RiskAssessment.created_at))
        .first()
    )


def analyze_transaction(db: Session, transaction_id: str) -> RiskAnalyzeResponse:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")

    txn_dict = transaction_to_dict(txn)
    fraud_prob = ml_service.predict_fraud_probability(txn_dict)
    result = compute_risk(txn_dict, fraud_prob)

    triggered_json = json.dumps([r.model_dump() for r in result["triggered_rules"]])
    assessment = RiskAssessment(
        transaction_id=transaction_id,
        fraud_probability=result["fraud_probability"],
        ml_score=result["ml_score"],
        rule_score=result["rule_score"],
        final_risk_score=result["final_risk_score"],
        risk_level=result["risk_level"],
        triggered_rules=triggered_json,
    )
    db.add(assessment)

    txn.risk_score = result["final_risk_score"]
    txn.risk_level = result["risk_level"]
    if txn.status == "PENDING":
        txn.status = "ANALYZED"
    db.commit()

    return RiskAnalyzeResponse(
        transaction_id=transaction_id,
        fraud_probability=result["fraud_probability"],
        ml_score=result["ml_score"],
        rule_score=result["rule_score"],
        risk_score=result["final_risk_score"],
        risk_level=result["risk_level"],
        triggered_rules=result["triggered_rules"],
        automated_action=None,
        requires_human_approval=False,
    )


def list_transactions(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    risk_level: str | None = None,
    status: str | None = None,
    search: str | None = None,
    minimum_risk: float | None = None,
    payment_method: str | None = None,
    merchant_category: str | None = None,
    sort_by: str = "risk_score",
    sort_order: str = "desc",
    critical_only: bool = False,
) -> PaginatedTransactions:
    query = db.query(Transaction)

    if critical_only:
        query = query.filter(Transaction.risk_level == "CRITICAL")
    elif risk_level:
        query = query.filter(Transaction.risk_level == risk_level.upper())

    if status:
        query = query.filter(Transaction.status == status.upper())
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)
    if merchant_category:
        query = query.filter(Transaction.merchant_category == merchant_category)
    if minimum_risk is not None:
        query = query.filter(Transaction.risk_score >= minimum_risk)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Transaction.transaction_id.ilike(pattern),
                Transaction.customer_id.ilike(pattern),
                Transaction.city.ilike(pattern),
            )
        )

    sort_col = {
        "risk_score": Transaction.risk_score,
        "amount": Transaction.transaction_amount,
        "date": Transaction.transaction_date,
    }.get(sort_by, Transaction.risk_score)

    if sort_order == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullsfirst())

    total = query.count()
    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()

    items = [
        TransactionSummary(
            transaction_id=r.transaction_id,
            customer_id=r.customer_id,
            transaction_amount=r.transaction_amount,
            payment_method=r.payment_method,
            city=r.city,
            country=r.country,
            merchant_category=r.merchant_category,
            risk_score=r.risk_score,
            risk_level=r.risk_level,
            status=r.status,
            transaction_date=r.transaction_date,
            is_fraud=r.is_fraud,
        )
        for r in rows
    ]

    return PaginatedTransactions(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
    )


def get_transaction_detail(db: Session, transaction_id: str) -> TransactionDetail:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")

    assessment = get_latest_assessment(db, transaction_id)
    triggered: list[TriggeredRule] = []
    fraud_prob = ml_score = rule_score = None

    if assessment:
        fraud_prob = assessment.fraud_probability
        ml_score = assessment.ml_score
        rule_score = assessment.rule_score
        triggered = [TriggeredRule(**r) for r in json.loads(assessment.triggered_rules)]

    return TransactionDetail(
        **transaction_to_dict(txn),
        fraud_probability=fraud_prob,
        ml_score=ml_score,
        rule_score=rule_score,
        triggered_rules=triggered,
    )


def get_customer_profile(db: Session, customer_id: str) -> CustomerProfile:
    txns = db.query(Transaction).filter(Transaction.customer_id == customer_id).all()
    if not txns:
        raise ValueError(f"Customer {customer_id} not found")

    latest = txns[0]
    return CustomerProfile(
        customer_id=customer_id,
        age=latest.customer_age,
        credit_score=latest.credit_score,
        account_age_years=latest.account_age_years,
        account_balance=latest.account_balance,
        transaction_freq_monthly=latest.transaction_freq_monthly,
        num_prev_transactions=latest.num_prev_transactions,
        total_transactions=len(txns),
        fraud_count=sum(1 for t in txns if t.is_fraud),
    )


def get_stats(db: Session) -> StatsResponse:
    total = db.query(Transaction).count()
    analyzed = db.query(Transaction).filter(Transaction.risk_score.isnot(None)).count()
    high_risk = db.query(Transaction).filter(Transaction.risk_level == "HIGH").count()
    critical = db.query(Transaction).filter(Transaction.risk_level == "CRITICAL").count()
    fraud_count = db.query(Transaction).filter(Transaction.is_fraud == True).count()  # noqa: E712

    amount_at_risk = (
        db.query(func.sum(Transaction.transaction_amount))
        .filter(Transaction.risk_level.in_(["HIGH", "CRITICAL"]))
        .scalar()
        or 0
    )

    fraud_rate = (fraud_count / total * 100) if total else 0

    return StatsResponse(
        transactions_analyzed=analyzed,
        high_risk_transactions=high_risk,
        critical_transactions=critical,
        amount_at_risk=float(amount_at_risk),
        fraud_detection_rate=round(fraud_rate, 2),
        total_transactions=total,
        fraud_count=fraud_count,
    )


def get_risk_summary(db: Session) -> RiskSummary:
    levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_distribution = {}
    amount_at_risk_by_level = {}

    for level in levels:
        count = db.query(Transaction).filter(Transaction.risk_level == level).count()
        risk_distribution[level] = count
        amt = (
            db.query(func.sum(Transaction.transaction_amount))
            .filter(Transaction.risk_level == level)
            .scalar()
            or 0
        )
        amount_at_risk_by_level[level] = float(amt)

    fraud_count = db.query(Transaction).filter(Transaction.is_fraud == True).count()  # noqa: E712
    legit_count = db.query(Transaction).filter(Transaction.is_fraud == False).count()  # noqa: E712

    category_rows = (
        db.query(Transaction.merchant_category, func.count(Transaction.id))
        .filter(Transaction.is_fraud == True)  # noqa: E712
        .group_by(Transaction.merchant_category)
        .order_by(desc(func.count(Transaction.id)))
        .limit(10)
        .all()
    )
    fraud_by_category = [{"category": c, "count": n} for c, n in category_rows]

    date_rows = (
        db.query(Transaction.transaction_date, func.avg(Transaction.risk_score), func.count(Transaction.id))
        .filter(Transaction.risk_score.isnot(None))
        .group_by(Transaction.transaction_date)
        .order_by(Transaction.transaction_date)
        .limit(30)
        .all()
    )
    risk_trend = [
        {"date": d, "avg_risk_score": round(float(avg or 0), 2), "count": n}
        for d, avg, n in date_rows
    ]

    return RiskSummary(
        risk_distribution=risk_distribution,
        fraud_vs_legitimate={"fraud": fraud_count, "legitimate": legit_count},
        risk_trend=risk_trend,
        fraud_by_category=fraud_by_category,
        amount_at_risk_by_level=amount_at_risk_by_level,
    )


def get_model_metrics() -> ModelMetrics:
    m = ml_service.metrics
    return ModelMetrics(
        model_type=ml_service.model_type,
        precision=m.get("precision", 0),
        recall=m.get("recall", 0),
        f1=m.get("f1", 0),
        roc_auc=m.get("roc_auc", 0),
        pr_auc=m.get("pr_auc"),
        confusion_matrix=m.get("confusion_matrix", [[0, 0], [0, 0]]),
        feature_count=len(ml_service.feature_names),
        trained_at=m.get("trained_at"),
    )


def apply_action(db: Session, transaction_id: str, action: str) -> ActionResponse:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")

    status_map = {
        "APPROVE": "APPROVED",
        "MONITOR": "MONITORING",
        "REQUIRE_VERIFICATION": "VERIFICATION_REQUIRED",
        "HOLD": "HELD",
        "BLOCK": "BLOCKED",
        "MANUAL_REVIEW": "MANUAL_REVIEW",
    }

    previous = txn.status
    new_status = status_map.get(action.upper(), action.upper())
    txn.status = new_status
    txn.action = action.upper()

    log = ActionLog(
        transaction_id=transaction_id,
        action=action.upper(),
        previous_status=previous,
        new_status=new_status,
    )
    db.add(log)
    db.commit()

    return ActionResponse(
        transaction_id=transaction_id,
        action=action.upper(),
        previous_status=previous,
        new_status=new_status,
        timestamp=log.created_at,
    )


def apply_agent_recommendation(db: Session, transaction_id: str, recommendation: str) -> tuple[str, str, bool]:
    """Apply the AI agent's decision, except BLOCK which always awaits a human."""
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")

    recommendation = recommendation.upper()
    status_map = {
        "APPROVE": "APPROVED",
        "MONITOR": "MONITORING",
        "REQUIRE_VERIFICATION": "VERIFICATION_REQUIRED",
        "HOLD": "HELD",
        "MANUAL_REVIEW": "MANUAL_REVIEW",
    }
    previous_status = txn.status
    if recommendation == "BLOCK":
        action_applied = "BLOCK_RECOMMENDED"
        new_status = "PENDING_HUMAN_APPROVAL"
        requires_human_approval = True
    else:
        action_applied = recommendation if recommendation in status_map else "MANUAL_REVIEW"
        new_status = status_map.get(action_applied, "MANUAL_REVIEW")
        requires_human_approval = False

    txn.action = action_applied
    txn.status = new_status
    db.add(ActionLog(
        transaction_id=transaction_id,
        action=f"AGENT_{action_applied}",
        previous_status=previous_status,
        new_status=new_status,
    ))
    db.commit()
    return action_applied, new_status, requires_human_approval


def apply_automated_policy(db: Session, txn: Transaction) -> tuple[str | None, bool]:
    """Apply safe automatic controls; critical cases are always routed to a human."""
    if txn.status not in {"PENDING", "ANALYZED"} or txn.action is not None:
        return None, txn.status == "PENDING_HUMAN_APPROVAL"

    policy = {
        "LOW": ("AUTO_APPROVE", "APPROVED", False),
        "MEDIUM": ("AUTO_MONITOR", "MONITORING", False),
        "HIGH": ("AUTO_HOLD", "HELD", False),
        # A BLOCK decision is intentionally never automated. An analyst must make it.
        "CRITICAL": ("ESCALATE_HUMAN_REVIEW", "PENDING_HUMAN_APPROVAL", True),
    }
    action, new_status, requires_human_approval = policy.get(
        txn.risk_level or "", ("ESCALATE_HUMAN_REVIEW", "PENDING_HUMAN_APPROVAL", True)
    )
    previous_status = txn.status
    txn.status = new_status
    txn.action = action
    db.add(ActionLog(
        transaction_id=txn.transaction_id,
        action=action,
        previous_status=previous_status,
        new_status=new_status,
    ))
    return action, requires_human_approval


def get_highest_risk_transaction_id(db: Session) -> str | None:
    txn = (
        db.query(Transaction)
        .filter(Transaction.risk_score.isnot(None))
        .order_by(desc(Transaction.risk_score))
        .first()
    )
    return txn.transaction_id if txn else None


def save_investigation(
    db: Session,
    transaction_id: str,
    report: InvestigationReport,
    is_fallback: bool = False,
):
    existing = db.query(Investigation).filter(Investigation.transaction_id == transaction_id).first()
    data = {
        "risk_level": report.risk_level,
        "confidence": report.confidence,
        "summary": report.summary,
        "primary_risk_factors": json.dumps(report.primary_risk_factors),
        "investigation_findings": json.dumps(report.investigation_findings),
        "recommended_action": report.recommended_action,
        "recommended_action_reason": report.recommended_action_reason,
        "requires_human_review": report.requires_human_review,
        "is_fallback": is_fallback,
        "tool_calls": json.dumps([t.model_dump() for t in report.tool_calls]),
    }
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        db.add(Investigation(transaction_id=transaction_id, **data))
    db.commit()


def get_investigation(db: Session, transaction_id: str) -> InvestigationResponse | None:
    inv = db.query(Investigation).filter(Investigation.transaction_id == transaction_id).first()
    if not inv:
        return None

    tool_calls_raw = json.loads(inv.tool_calls) if inv.tool_calls else []
    report = InvestigationReport(
        risk_level=inv.risk_level,
        confidence=inv.confidence,
        summary=inv.summary,
        primary_risk_factors=json.loads(inv.primary_risk_factors),
        investigation_findings=json.loads(inv.investigation_findings),
        recommended_action=inv.recommended_action,
        recommended_action_reason=inv.recommended_action_reason,
        requires_human_review=inv.requires_human_review,
        tool_calls=[ToolCallRecord(**t) for t in tool_calls_raw],
    )
    return InvestigationResponse(
        transaction_id=transaction_id,
        investigation=report,
        is_fallback=inv.is_fallback,
    )
