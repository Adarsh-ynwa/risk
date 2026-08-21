"""FastAPI application entry point."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.investigator import run_investigation
from app.agent.tools import get_filter_options, get_fraud_probability_distribution
from app.config import settings
from app.database import Base, engine, get_db
from app.models.db_models import ActionLog, Investigation, RiskAssessment, Transaction
from app.schemas.schemas import (
    ActionRequest,
    ActionResponse,
    HealthResponse,
    InvestigationResponse,
    ModelMetrics,
    PaginatedTransactions,
    RiskAnalyzeRequest,
    RiskAnalyzeResponse,
    RiskSummary,
    StatsResponse,
    TransactionCreateRequest,
    TransactionDetail,
)
from app.services.ml_service import ml_service
from app.services.transaction_service import (
    analyze_transaction,
    apply_agent_recommendation,
    apply_action,
    get_customer_profile,
    get_highest_risk_transaction_id,
    get_investigation,
    get_latest_assessment,
    get_model_metrics,
    get_risk_summary,
    get_stats,
    get_transaction_detail,
    list_transactions,
    save_investigation,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE investigations ADD COLUMN tool_calls TEXT DEFAULT '[]'"))
            conn.commit()
        except Exception:
            pass
    loaded = ml_service.load()
    logger.info("ML model loaded: %s", loaded)
    yield


app = FastAPI(
    title="AI Risk Manager API",
    description="Experimental AI-powered payment risk management prototype",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        model_loaded=ml_service.is_loaded,
        database_connected=db_ok,
        groq_configured=bool(settings.groq_api_key),
    )


@app.get("/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@app.get("/transactions", response_model=PaginatedTransactions)
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    risk_level: str | None = None,
    status: str | None = None,
    search: str | None = None,
    minimum_risk: float | None = None,
    payment_method: str | None = None,
    merchant_category: str | None = None,
    sort_by: str = "risk_score",
    sort_order: str = "desc",
    critical_only: bool = False,
    db: Session = Depends(get_db),
):
    return list_transactions(
        db, page, page_size, risk_level, status, search,
        minimum_risk, payment_method, merchant_category,
        sort_by, sort_order, critical_only,
    )


@app.get("/transactions/highest-risk")
def highest_risk_transaction(db: Session = Depends(get_db)):
    txn_id = get_highest_risk_transaction_id(db)
    if not txn_id:
        raise HTTPException(404, "No analyzed transactions found")
    return {"transaction_id": txn_id}


@app.get("/transactions/filters")
def transaction_filters(db: Session = Depends(get_db)):
    return get_filter_options(db)


@app.post("/transactions", response_model=RiskAnalyzeResponse, status_code=201)
def create_transaction(body: TransactionCreateRequest, db: Session = Depends(get_db)):
    """Persist an incoming payment, then score it immediately."""
    now = datetime.now()
    txn = Transaction(
        transaction_id=f"TXN-{uuid4().hex[:12].upper()}",
        customer_id=body.customer_id.strip(),
        transaction_date=now.date().isoformat(),
        transaction_time=now.strftime("%H:%M:%S"),
        hour_of_day=now.hour,
        is_weekend=now.weekday() >= 5,
        is_night_transaction=now.hour < 6 or now.hour >= 22,
        country=body.country.strip(),
        city=body.city.strip(),
        merchant_category=body.merchant_category.strip(),
        payment_method=body.payment_method.strip(),
        device_type=body.device_type.strip(),
        customer_age=body.customer_age,
        credit_score=body.credit_score,
        account_age_years=body.account_age_years,
        account_balance=body.account_balance,
        transaction_amount=body.transaction_amount,
        num_prev_transactions=body.num_prev_transactions,
        transaction_freq_monthly=body.transaction_freq_monthly,
        distance_from_home_km=body.distance_from_home_km,
        time_since_last_txn_hrs=body.time_since_last_txn_hrs,
        is_international=body.is_international,
        failed_attempts=body.failed_attempts,
        pin_changed_recently=body.pin_changed_recently,
        is_fraud=False,
        status="PENDING",
    )
    db.add(txn)
    db.commit()
    return analyze_transaction(db, txn.transaction_id)


@app.get("/transactions/{transaction_id}", response_model=TransactionDetail)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    try:
        return get_transaction_detail(db, transaction_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    try:
        return get_customer_profile(db, customer_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/risk/analyze", response_model=RiskAnalyzeResponse)
def risk_analyze(body: RiskAnalyzeRequest, db: Session = Depends(get_db)):
    try:
        return analyze_transaction(db, body.transaction_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/investigations/{transaction_id}", response_model=InvestigationResponse)
def create_investigation(transaction_id: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        raise HTTPException(404, f"Transaction {transaction_id} not found")

    assessment = get_latest_assessment(db, transaction_id)
    if not assessment:
        raise HTTPException(
            400,
            "Transaction must be analyzed before investigation. Call POST /risk/analyze first.",
        )
    triggered_rules = json.loads(assessment.triggered_rules)
    risk_assessment = {
        "fraud_probability": assessment.fraud_probability,
        "ml_score": assessment.ml_score,
        "rule_score": assessment.rule_score,
        "final_risk_score": assessment.final_risk_score,
        "risk_level": assessment.risk_level,
        "triggered_rules": triggered_rules,
    }

    try:
        report, is_fallback = run_investigation(db, transaction_id, txn.customer_id, risk_assessment)
        save_investigation(db, transaction_id, report, is_fallback)
        action_applied, final_status, requires_human_approval = apply_agent_recommendation(
            db, transaction_id, report.recommended_action
        )
        return InvestigationResponse(
            transaction_id=transaction_id,
            investigation=report,
            is_fallback=is_fallback,
            final_status=final_status,
            action_applied=action_applied,
            requires_human_approval=requires_human_approval,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/investigations/{transaction_id}", response_model=InvestigationResponse)
def read_investigation(transaction_id: str, db: Session = Depends(get_db)):
    result = get_investigation(db, transaction_id)
    if not result:
        raise HTTPException(404, "Investigation not found")
    return result


@app.get("/risk/summary", response_model=RiskSummary)
def risk_summary(db: Session = Depends(get_db)):
    return get_risk_summary(db)


@app.get("/model/metrics", response_model=ModelMetrics)
def model_metrics():
    return get_model_metrics()


@app.post("/actions/{transaction_id}", response_model=ActionResponse)
def create_action(transaction_id: str, body: ActionRequest, db: Session = Depends(get_db)):
    try:
        return apply_action(db, transaction_id, body.action.value)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/actions")
def list_actions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(ActionLog).order_by(ActionLog.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "transaction_id": r.transaction_id,
                "action": r.action,
                "previous_status": r.previous_status,
                "new_status": r.new_status,
                "timestamp": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    stats_data = get_stats(db)
    summary = get_risk_summary(db)

    intl_fraud = db.query(Transaction).filter(
        Transaction.is_international == True,  # noqa: E712
        Transaction.is_fraud == True,  # noqa: E712
    ).count()
    night_fraud = db.query(Transaction).filter(
        Transaction.is_night_transaction == True,  # noqa: E712
        Transaction.is_fraud == True,  # noqa: E712
    ).count()
    failed_corr = db.query(Transaction).filter(
        Transaction.failed_attempts >= 2,
        Transaction.is_fraud == True,  # noqa: E712
    ).count()

    return {
        "stats": stats_data.model_dump(),
        "risk_summary": summary.model_dump(),
        "international_fraud_count": intl_fraud,
        "night_transaction_fraud_count": night_fraud,
        "failed_attempt_fraud_count": failed_corr,
        "fraud_probability_distribution": get_fraud_probability_distribution(db),
    }
