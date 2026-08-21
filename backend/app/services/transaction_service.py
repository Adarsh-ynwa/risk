"""Application services for transactions, risk, and analytics."""

import json
import statistics
from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session

from app.models.db_models import ActionLog, Investigation, RiskAssessment, Transaction, UnblockRequest, Verification
from app.schemas.schemas import (
    ActionResponse,
    BehaviorSignal,
    CustomerBehaviorResponse,
    CustomerProfile,
    InvestigationReport,
    InvestigationResponse,
    ModelMetrics,
    PaginatedTransactions,
    RiskAnalyzeResponse,
    RiskSummary,
    StatsResponse,
    ToolCallRecord,
    TimelineEvent,
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


def get_customer_behavior(db: Session, transaction_id: str) -> CustomerBehaviorResponse:
    """Compare a transaction with only that customer's earlier transactions."""
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    history = (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == txn.customer_id,
            Transaction.transaction_id != transaction_id,
            or_(
                Transaction.transaction_date < txn.transaction_date,
                (Transaction.transaction_date == txn.transaction_date)
                & (Transaction.transaction_time < txn.transaction_time),
            ),
        )
        .order_by(desc(Transaction.transaction_date), desc(Transaction.transaction_time))
        .limit(200)
        .all()
    )
    if not history:
        return CustomerBehaviorResponse(
            transaction_id=transaction_id,
            customer_id=txn.customer_id,
            history_count=0,
            amount_ratio_to_median=None,
            is_new_country=True,
            is_new_city=True,
            is_new_device=True,
            is_new_merchant_category=True,
            signals=[BehaviorSignal(
                label="Customer history",
                current_value="First observed transaction",
                baseline_value="No earlier activity",
                impact="INCREASES_RISK",
                explanation="No earlier customer activity is available to establish normal behavior.",
            )],
        )

    median_amount = float(statistics.median(row.transaction_amount for row in history))
    amount_ratio = txn.transaction_amount / max(median_amount, 1)
    countries = {row.country for row in history}
    cities = {row.city for row in history}
    devices = {row.device_type for row in history}
    categories = {row.merchant_category for row in history}
    median_hour = float(statistics.median(row.hour_of_day for row in history))
    is_new_country = txn.country not in countries
    is_new_city = txn.city not in cities
    is_new_device = txn.device_type not in devices
    is_new_category = txn.merchant_category not in categories

    signals = [BehaviorSignal(
        label="Transaction amount",
        current_value=f"₹{txn.transaction_amount:,.0f}",
        baseline_value=f"₹{median_amount:,.0f} customer median",
        impact="INCREASES_RISK" if amount_ratio >= 3 else "REDUCES_RISK",
        explanation=(f"The amount is {amount_ratio:.1f}× the customer's earlier median." if amount_ratio >= 3
                     else f"The amount is within {amount_ratio:.1f}× of the customer's earlier median."),
    )]
    for label, current, baseline, is_new in [
        ("Country", txn.country, ", ".join(sorted(countries)[:3]), is_new_country),
        ("City", txn.city, ", ".join(sorted(cities)[:3]), is_new_city),
        ("Device type", txn.device_type, ", ".join(sorted(devices)), is_new_device),
        ("Merchant category", txn.merchant_category, ", ".join(sorted(categories)[:3]), is_new_category),
    ]:
        signals.append(BehaviorSignal(
            label=label,
            current_value=current,
            baseline_value=baseline or "No baseline",
            impact="INCREASES_RISK" if is_new else "REDUCES_RISK",
            explanation=f"{label} is {'new for this customer' if is_new else 'present in earlier customer activity'}.",
        ))
    unusual_hour = abs(txn.hour_of_day - median_hour) >= 6
    signals.append(BehaviorSignal(
        label="Transaction time",
        current_value=f"{txn.hour_of_day:02d}:00",
        baseline_value=f"Typical hour around {int(median_hour):02d}:00",
        impact="INCREASES_RISK" if unusual_hour else "REDUCES_RISK",
        explanation="The time differs substantially from earlier activity." if unusual_hour else "The time is consistent with earlier activity.",
    ))
    return CustomerBehaviorResponse(
        transaction_id=transaction_id,
        customer_id=txn.customer_id,
        history_count=len(history),
        amount_ratio_to_median=round(amount_ratio, 2),
        is_new_country=is_new_country,
        is_new_city=is_new_city,
        is_new_device=is_new_device,
        is_new_merchant_category=is_new_category,
        signals=signals,
    )


def get_case_timeline(db: Session, transaction_id: str) -> list[TimelineEvent]:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    events = [TimelineEvent(event_type="TRANSACTION", title="Transaction received",
        description=f"Payment of ₹{txn.transaction_amount:,.0f} was received for risk analysis.",
        actor="Payment gateway", status="RECEIVED", timestamp=txn.created_at)]
    for row in db.query(RiskAssessment).filter(RiskAssessment.transaction_id == transaction_id).all():
        events.append(TimelineEvent(event_type="ASSESSMENT", title="Risk assessment completed",
            description=f"Hybrid risk score {row.final_risk_score:.1f}/100 ({row.risk_level}).",
            actor="ML model + rules", status=row.risk_level, timestamp=row.created_at))
    for row in db.query(Investigation).filter(Investigation.transaction_id == transaction_id).all():
        events.append(TimelineEvent(event_type="INVESTIGATION", title="AI investigation completed",
            description=f"Recommended {row.recommended_action.replace('_', ' ').lower()} with {row.confidence:.0%} confidence.",
            actor="AI Risk Investigator", status=row.recommended_action, timestamp=row.created_at))
    for row in db.query(Verification).filter(Verification.transaction_id == transaction_id).all():
        events.append(TimelineEvent(event_type="VERIFICATION", title=f"{row.method.replace('_', ' ').title()} requested",
            description=row.notes or "Additional customer verification was requested.", actor=row.requested_by,
            status="PENDING", timestamp=row.created_at))
        if row.resolved_at:
            events.append(TimelineEvent(event_type="VERIFICATION_RESULT", title=f"Verification {row.status.lower()}",
                description=row.notes or f"Verification finished with status {row.status}.",
                actor=row.resolved_by or "Demo Analyst", status=row.status, timestamp=row.resolved_at))
    for row in db.query(UnblockRequest).filter(UnblockRequest.transaction_id == transaction_id).all():
        events.append(TimelineEvent(event_type="UNBLOCK_REQUEST", title="Unblock review requested",
            description=row.reason, actor=row.requested_by, status="PENDING", timestamp=row.created_at))
        if row.reviewed_at:
            events.append(TimelineEvent(event_type="UNBLOCK_REVIEW", title=f"Unblock request {row.status.lower()}",
                description=row.review_notes or f"Senior review finished with status {row.status}.",
                actor=row.reviewed_by or "Senior Demo Analyst", status=row.status, timestamp=row.reviewed_at))
    for row in db.query(ActionLog).filter(ActionLog.transaction_id == transaction_id).all():
        events.append(TimelineEvent(event_type="ACTION", title=row.action.replace("_", " ").title(),
            description=f"Status changed from {row.previous_status} to {row.new_status}.",
            actor="AI Risk Manager" if row.action.startswith(("AGENT_", "AUTO_")) else "Demo Analyst",
            status=row.new_status, timestamp=row.created_at))
    return sorted(events, key=lambda event: event.timestamp)


def create_verification(db: Session, transaction_id: str, method: str, requested_by: str, notes: str | None) -> Verification:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    if txn.status in {"BLOCKED", "UNBLOCK_PENDING"}:
        raise ValueError("Blocked transactions cannot enter verification. A separate authorized unblock review is required.")
    previous = txn.status
    row = Verification(transaction_id=transaction_id, method=method, requested_by=requested_by, notes=notes)
    txn.status = "VERIFICATION_REQUIRED"
    txn.action = "REQUIRE_VERIFICATION"
    db.add(row)
    db.add(ActionLog(transaction_id=transaction_id, action=f"REQUEST_{method}", previous_status=previous, new_status=txn.status))
    db.commit()
    db.refresh(row)
    return row


def resolve_verification(db: Session, verification_id: int, status: str, resolved_by: str, notes: str | None) -> Verification:
    row = db.query(Verification).filter(Verification.id == verification_id).first()
    if not row:
        raise ValueError(f"Verification {verification_id} not found")
    if row.status != "PENDING":
        raise ValueError("Verification has already been resolved")
    txn = db.query(Transaction).filter(Transaction.transaction_id == row.transaction_id).first()
    if txn.status in {"BLOCKED", "UNBLOCK_PENDING"}:
        raise ValueError("Verification cannot change a blocked transaction.")
    previous = txn.status
    status_map = {"PASSED": "VERIFIED", "FAILED": "HELD", "EXPIRED": "MANUAL_REVIEW", "CANCELLED": "ANALYZED"}
    row.status, row.resolved_by, row.resolved_at = status, resolved_by, datetime.now()
    if notes:
        row.notes = notes
    txn.status, txn.action = status_map[status], f"VERIFICATION_{status}"
    db.add(ActionLog(transaction_id=txn.transaction_id, action=f"VERIFICATION_{status}", previous_status=previous, new_status=txn.status))
    db.commit()
    db.refresh(row)
    return row


def request_unblock(db: Session, transaction_id: str, reason: str, requested_by: str) -> UnblockRequest:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    if txn.status != "BLOCKED":
        raise ValueError("Only blocked transactions can request an unblock review.")
    pending = db.query(UnblockRequest).filter(
        UnblockRequest.transaction_id == transaction_id,
        UnblockRequest.status == "PENDING",
    ).first()
    if pending:
        raise ValueError("An unblock review is already pending.")
    row = UnblockRequest(transaction_id=transaction_id, reason=reason, requested_by=requested_by)
    txn.status = "UNBLOCK_PENDING"
    db.add(row)
    db.add(ActionLog(transaction_id=transaction_id, action="UNBLOCK_REQUESTED", previous_status="BLOCKED", new_status="UNBLOCK_PENDING"))
    db.commit()
    db.refresh(row)
    return row


def review_unblock(db: Session, request_id: int, decision: str, reviewed_by: str, notes: str | None) -> UnblockRequest:
    row = db.query(UnblockRequest).filter(UnblockRequest.id == request_id).first()
    if not row:
        raise ValueError(f"Unblock request {request_id} not found")
    if row.status != "PENDING":
        raise ValueError("Unblock request has already been reviewed.")
    txn = db.query(Transaction).filter(Transaction.transaction_id == row.transaction_id).first()
    if txn.status != "UNBLOCK_PENDING":
        raise ValueError("Transaction is not awaiting unblock review.")
    approved = decision == "APPROVE"
    row.status = "APPROVED" if approved else "REJECTED"
    row.reviewed_by = reviewed_by
    row.review_notes = notes
    row.reviewed_at = datetime.now()
    new_status = "MANUAL_REVIEW" if approved else "BLOCKED"
    txn.status = new_status
    txn.action = "UNBLOCK_APPROVED" if approved else "UNBLOCK_REJECTED"
    db.add(ActionLog(transaction_id=txn.transaction_id, action=txn.action, previous_status="UNBLOCK_PENDING", new_status=new_status))
    db.commit()
    db.refresh(row)
    return row


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

    fraud_prevalence = (fraud_count / total * 100) if total else 0

    return StatsResponse(
        transactions_analyzed=analyzed,
        high_risk_transactions=high_risk,
        critical_transactions=critical,
        amount_at_risk=float(amount_at_risk),
        fraud_prevalence_rate=round(fraud_prevalence, 2),
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
        threshold=m.get("threshold", 0.5),
        false_positives=m.get("false_positives", 0),
        false_negatives=m.get("false_negatives", 0),
        true_positives=m.get("true_positives", 0),
        true_negatives=m.get("true_negatives", 0),
        alert_rate=m.get("alert_rate", 0),
        estimated_total_cost_inr=m.get("estimated_total_cost_inr", 0),
        false_positive_cost_inr=m.get("false_positive_cost_inr", 0),
        false_negative_cost_inr=m.get("false_negative_cost_inr", 0),
        validation_size=m.get("validation_size", 0),
        test_size=m.get("test_size", 0),
        split_strategy=m.get("split_strategy", "unknown"),
        threshold_selected_on=m.get("threshold_selected_on", "unknown"),
        cost_assumptions_inr=m.get("cost_assumptions_inr", {}),
        validation_threshold_comparison=m.get("validation_threshold_comparison", []),
        hybrid_test_metrics=m.get("hybrid_test_metrics", {}),
    )


def apply_action(db: Session, transaction_id: str, action: str) -> ActionResponse:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise ValueError(f"Transaction {transaction_id} not found")
    if txn.status in {"BLOCKED", "UNBLOCK_PENDING"} and action.upper() != "BLOCK":
        raise ValueError("Blocked transactions are terminal. A separate authorized unblock review is required.")

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
    if txn.status in {"BLOCKED", "UNBLOCK_PENDING"}:
        return "BLOCK_RETAINED", "BLOCKED", True

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
