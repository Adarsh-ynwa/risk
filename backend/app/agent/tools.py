"""Agent tools for AI Risk Investigator."""

import json
from typing import Any, Callable

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.db_models import RiskAssessment, Transaction
from app.services.transaction_service import get_customer_behavior, get_customer_profile, transaction_to_dict


def get_customer_profile_tool(db: Session, customer_id: str) -> dict[str, Any]:
    profile = get_customer_profile(db, customer_id)
    return profile.model_dump()


def get_customer_transaction_history(db: Session, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(desc(Transaction.transaction_date), desc(Transaction.transaction_time))
        .limit(limit)
        .all()
    )
    return [
        {
            "transaction_id": r.transaction_id,
            "amount": r.transaction_amount,
            "date": r.transaction_date,
            "merchant_category": r.merchant_category,
            "payment_method": r.payment_method,
            "city": r.city,
            "is_fraud": r.is_fraud,
            "risk_level": r.risk_level,
            "status": r.status,
        }
        for r in rows
    ]


def get_transaction_context_tool(db: Session, transaction_id: str) -> dict[str, Any]:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        return {"error": f"Transaction {transaction_id} not found"}
    return transaction_to_dict(txn)


def get_customer_behavior_tool(db: Session, transaction_id: str) -> dict[str, Any]:
    return get_customer_behavior(db, transaction_id).model_dump()


def get_customer_risk_history(db: Session, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    txn_ids = [
        t.transaction_id
        for t in db.query(Transaction.transaction_id)
        .filter(Transaction.customer_id == customer_id)
        .limit(50)
        .all()
    ]
    if not txn_ids:
        return []

    assessments = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.transaction_id.in_(txn_ids))
        .order_by(desc(RiskAssessment.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "transaction_id": a.transaction_id,
            "fraud_probability": a.fraud_probability,
            "final_risk_score": a.final_risk_score,
            "risk_level": a.risk_level,
            "rule_score": a.rule_score,
            "created_at": a.created_at.isoformat(),
        }
        for a in assessments
    ]


def get_similar_transactions(db: Session, transaction_id: str, limit: int = 5) -> list[dict[str, Any]]:
    txn = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not txn:
        return []

    amount = txn.transaction_amount
    category = txn.merchant_category
    low = amount * 0.5
    high = amount * 1.5

    similar = (
        db.query(Transaction)
        .filter(
            Transaction.transaction_id != transaction_id,
            Transaction.merchant_category == category,
            Transaction.transaction_amount.between(low, high),
        )
        .order_by(desc(Transaction.risk_score))
        .limit(limit)
        .all()
    )

    if len(similar) < limit:
        extra = (
            db.query(Transaction)
            .filter(
                Transaction.transaction_id != transaction_id,
                Transaction.is_international == txn.is_international,
            )
            .order_by(desc(Transaction.risk_score))
            .limit(limit - len(similar))
            .all()
        )
        seen = {s.transaction_id for s in similar}
        similar.extend(e for e in extra if e.transaction_id not in seen)

    return [
        {
            "transaction_id": s.transaction_id,
            "amount": s.transaction_amount,
            "merchant_category": s.merchant_category,
            "city": s.city,
            "is_fraud": s.is_fraud,
            "risk_level": s.risk_level,
            "risk_score": s.risk_score,
            "payment_method": s.payment_method,
        }
        for s in similar[:limit]
    ]


TOOL_DEFINITIONS = [
    {
        "name": "get_transaction_context",
        "description": "Get complete context for the transaction under investigation including amount, location, device, and flags.",
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "description": "Transaction ID to look up"},
            },
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_customer_behavior",
        "description": "Compare the transaction with the customer's earlier behavior and return risk-increasing and risk-reducing evidence.",
        "parameters": {
            "type": "object",
            "properties": {"transaction_id": {"type": "string", "description": "Transaction ID to compare"}},
            "required": ["transaction_id"],
        },
    },
    {
        "name": "get_customer_profile",
        "description": "Get customer profile: age, credit score, account age, balance, transaction frequency, prior transaction count.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_customer_transaction_history",
        "description": "Get recent transaction history for a customer to detect behavioral anomalies.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
                "limit": {"type": "integer", "description": "Max transactions to return", "default": 10},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_customer_risk_history",
        "description": "Get prior risk assessments for this customer to identify repeat high-risk patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
                "limit": {"type": "integer", "description": "Max assessments to return", "default": 10},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_similar_transactions",
        "description": "Find similar transactions by amount and merchant category to compare fraud patterns.",
        "parameters": {
            "type": "object",
            "properties": {
                "transaction_id": {"type": "string", "description": "Reference transaction ID"},
                "limit": {"type": "integer", "description": "Max similar transactions", "default": 5},
            },
            "required": ["transaction_id"],
        },
    },
]


def execute_tool(db: Session, tool_name: str, args: dict[str, Any]) -> Any:
    """Dispatch a tool call by name."""
    dispatch: dict[str, Callable] = {
        "get_customer_profile": lambda: get_customer_profile_tool(db, args["customer_id"]),
        "get_customer_transaction_history": lambda: get_customer_transaction_history(
            db, args["customer_id"], args.get("limit", 10)
        ),
        "get_transaction_context": lambda: get_transaction_context_tool(db, args["transaction_id"]),
        "get_customer_behavior": lambda: get_customer_behavior_tool(db, args["transaction_id"]),
        "get_customer_risk_history": lambda: get_customer_risk_history(
            db, args["customer_id"], args.get("limit", 10)
        ),
        "get_similar_transactions": lambda: get_similar_transactions(
            db, args["transaction_id"], args.get("limit", 5)
        ),
    }
    if tool_name not in dispatch:
        return {"error": f"Unknown tool: {tool_name}"}
    return dispatch[tool_name]()


def get_fraud_probability_distribution(db: Session) -> list[dict[str, Any]]:
    """Bucket fraud probabilities from risk assessments for analytics chart."""
    assessments = db.query(RiskAssessment.fraud_probability).all()
    if not assessments:
        return []

    buckets = [
        ("0-10%", 0.0, 0.10),
        ("10-20%", 0.10, 0.20),
        ("20-40%", 0.20, 0.40),
        ("40-60%", 0.40, 0.60),
        ("60-80%", 0.60, 0.80),
        ("80-100%", 0.80, 1.01),
    ]
    counts = {label: 0 for label, _, _ in buckets}
    for (prob,) in assessments:
        for label, low, high in buckets:
            if low <= prob < high:
                counts[label] += 1
                break
    return [{"bucket": label, "count": counts[label]} for label, _, _ in buckets]


def get_filter_options(db: Session) -> dict[str, list[str]]:
    """Distinct filter values for transaction list UI."""
    payment_methods = [
        r[0] for r in db.query(Transaction.payment_method).distinct().order_by(Transaction.payment_method).all()
    ]
    merchant_categories = [
        r[0] for r in db.query(Transaction.merchant_category).distinct().order_by(Transaction.merchant_category).all()
    ]
    statuses = [
        r[0] for r in db.query(Transaction.status).distinct().order_by(Transaction.status).all()
    ]
    return {
        "payment_methods": payment_methods,
        "merchant_categories": merchant_categories,
        "statuses": statuses,
    }
