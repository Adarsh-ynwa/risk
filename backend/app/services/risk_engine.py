"""Risk scoring engine combining ML and deterministic rules."""

from typing import Any

from app.schemas.schemas import TriggeredRule
from app.services.rule_engine import evaluate_rules


def score_to_level(score: float) -> str:
    if score <= 29:
        return "LOW"
    if score <= 59:
        return "MEDIUM"
    if score <= 79:
        return "HIGH"
    return "CRITICAL"


def compute_risk(
    transaction: dict[str, Any],
    fraud_probability: float,
) -> dict[str, Any]:
    """
    Combine ML fraud probability with rule engine score.

    ml_score = fraud_probability * 100
    final_risk_score = 0.60 * ml_score + 0.40 * rule_score (clamped 0-100)
    """
    ml_score = fraud_probability * 100
    rule_score, triggered_rules = evaluate_rules(transaction)
    weighted_score = 0.60 * ml_score + 0.40 * rule_score

    # Safety override: a combination of several deterministic fraud signals is
    # actionable even when the statistical model has low confidence. This is
    # common in payment-risk systems, where hard rules protect against novel
    # fraud patterns that were underrepresented in model training data.
    # Preserve a safety floor for dense rule matches without forcing every
    # strongly suspicious payment to 100. A perfect rule score establishes a
    # 92-point floor; the ML evidence can still move the final score higher.
    rule_floor = 80 + (rule_score - 80) * 0.60 if rule_score >= 80 else 0
    final_risk_score = min(max(weighted_score, rule_floor, 0), 100)
    risk_level = score_to_level(final_risk_score)

    return {
        "transaction_id": transaction.get("transaction_id", ""),
        "fraud_probability": round(fraud_probability, 4),
        "ml_score": round(ml_score, 2),
        "rule_score": round(rule_score, 2),
        "final_risk_score": round(final_risk_score, 2),
        "risk_level": risk_level,
        "triggered_rules": triggered_rules,
    }


def risk_level_from_score(score: float) -> str:
    return score_to_level(score)
