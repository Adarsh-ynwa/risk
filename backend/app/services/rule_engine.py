"""Deterministic rule engine for payment risk scoring."""

from typing import Any

from app.schemas.schemas import TriggeredRule


def _rule(
    rule_id: str,
    name: str,
    severity: str,
    points: int,
    explanation: str,
    triggered: bool,
) -> TriggeredRule | None:
    if not triggered:
        return None
    return TriggeredRule(
        rule_id=rule_id,
        name=name,
        severity=severity,
        points=points,
        explanation=explanation,
    )


def evaluate_rules(transaction: dict[str, Any]) -> tuple[float, list[TriggeredRule]]:
    """
    Evaluate all deterministic risk rules against a transaction.
    Returns (rule_score capped at 100, list of triggered rules).
    """
    amount = float(transaction.get("transaction_amount", 0))
    balance = float(transaction.get("account_balance", 1))
    failed = int(transaction.get("failed_attempts", 0))
    distance = float(transaction.get("distance_from_home_km", 0))
    account_age = float(transaction.get("account_age_years", 1))
    freq = float(transaction.get("transaction_freq_monthly", 0))
    num_prev = int(transaction.get("num_prev_transactions", 0))

    rules: list[TriggeredRule | None] = [
        _rule(
            "R001",
            "Large Transaction",
            "HIGH",
            20,
            f"Transaction amount ₹{amount:,.0f} is unusually high relative to account balance ₹{balance:,.0f}.",
            amount > balance * 0.5 or amount > 50000,
        ),
        _rule(
            "R002",
            "International Transaction",
            "MEDIUM",
            10,
            "This is an international transaction, which carries elevated fraud risk.",
            bool(transaction.get("is_international")),
        ),
        _rule(
            "R003",
            "Night Transaction",
            "MEDIUM",
            10,
            "Transaction occurred during night hours (typically 10 PM – 6 AM).",
            bool(transaction.get("is_night_transaction")),
        ),
        _rule(
            "R004",
            "Multiple Failed Attempts",
            "HIGH",
            15,
            f"{failed} failed payment attempts were detected before this transaction.",
            failed >= 2,
        ),
        _rule(
            "R005",
            "Recent PIN Change",
            "MEDIUM",
            10,
            "Customer recently changed their PIN, which may indicate account compromise.",
            bool(transaction.get("pin_changed_recently")),
        ),
        _rule(
            "R006",
            "Unusual Distance",
            "HIGH",
            15,
            f"Transaction location is {distance:.0f} km from customer's home — unusually far.",
            distance > 200,
        ),
        _rule(
            "R007",
            "Low Account Age + Large Transaction",
            "HIGH",
            10,
            f"New account ({account_age:.1f} years) with large transaction ₹{amount:,.0f}.",
            account_age < 1 and amount > 10000,
        ),
        _rule(
            "R008",
            "High Transaction Frequency",
            "MEDIUM",
            10,
            f"Customer has unusually high transaction frequency ({freq:.0f}/month).",
            freq > 30 or (num_prev > 0 and freq / max(num_prev, 1) > 0.5),
        ),
    ]

    triggered = [r for r in rules if r is not None]
    rule_score = min(sum(r.points for r in triggered), 100)
    return rule_score, triggered
