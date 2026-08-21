"""
Explainable feature engineering for fraud detection.

Each feature is documented with its formula and business meaning.
"""

import numpy as np
import pandas as pd


def safe_divide(numerator: pd.Series | float, denominator: pd.Series | float, fill: float = 0.0) -> pd.Series:
    """Divide safely, avoiding division by zero."""
    if isinstance(numerator, pd.Series):
        result = np.where(denominator != 0, numerator / denominator, fill)
        return pd.Series(result, index=numerator.index)
    if denominator == 0:
        return fill
    return numerator / denominator


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add explainable derived features to transaction dataframe.

    Features:
    - amount_to_balance_ratio: transaction_amount / max(account_balance, 1)
      High ratio indicates transaction is large relative to available balance.

    - amount_to_previous_transaction_ratio: transaction_amount / avg_prev_amount
      Uses num_prev_transactions and balance as proxy when avg not available.
      High ratio suggests unusual spending spike.

    - night_risk_indicator: 1 if is_night_transaction else 0
      Night transactions carry elevated fraud risk.

    - international_risk_indicator: 1 if is_international else 0
      Cross-border transactions have higher fraud rates.

    - failed_attempt_risk: min(failed_attempts * 5, 25) / 25
      Normalized failed attempt score (0-1).

    - distance_risk: min(distance_from_home_km / 500, 1)
      Normalized distance from home (0-1, capped at 500km).

    - account_age_risk: 1 / max(account_age_years, 0.1)
      Inverse account age — newer accounts are riskier.

    - transaction_frequency_risk: min(transaction_freq_monthly / 50, 1)
      High frequency may indicate account takeover or card testing.
    """
    out = df.copy()

    out["amount_to_balance_ratio"] = safe_divide(
        out["transaction_amount"],
        out["account_balance"].clip(lower=1),
    )

    avg_prev = safe_divide(
        out["account_balance"],
        out["num_prev_transactions"].clip(lower=1),
    )
    out["amount_to_previous_transaction_ratio"] = safe_divide(
        out["transaction_amount"],
        avg_prev.clip(lower=1),
    )

    out["night_risk_indicator"] = out["is_night_transaction"].astype(int)
    out["international_risk_indicator"] = out["is_international"].astype(int)

    out["failed_attempt_risk"] = (out["failed_attempts"] * 5).clip(upper=25) / 25.0
    out["distance_risk"] = (out["distance_from_home_km"] / 500.0).clip(upper=1.0)
    out["account_age_risk"] = 1.0 / out["account_age_years"].clip(lower=0.1)
    out["transaction_frequency_risk"] = (out["transaction_freq_monthly"] / 50.0).clip(upper=1.0)

    return out


ENGINEERED_FEATURE_NAMES = [
    "amount_to_balance_ratio",
    "amount_to_previous_transaction_ratio",
    "night_risk_indicator",
    "international_risk_indicator",
    "failed_attempt_risk",
    "distance_risk",
    "account_age_risk",
    "transaction_frequency_risk",
]

BASE_NUMERIC_FEATURES = [
    "hour_of_day",
    "is_weekend",
    "is_night_transaction",
    "customer_age",
    "credit_score",
    "account_age_years",
    "account_balance",
    "transaction_amount",
    "num_prev_transactions",
    "transaction_freq_monthly",
    "distance_from_home_km",
    "time_since_last_txn_hrs",
    "is_international",
    "failed_attempts",
    "pin_changed_recently",
]

CATEGORICAL_FEATURES = [
    "country",
    "city",
    "merchant_category",
    "payment_method",
    "device_type",
]

EXCLUDE_COLUMNS = [
    "transaction_id",
    "customer_id",
    "transaction_date",
    "transaction_time",
    "is_fraud",
    "fraud_type",
    "risk_score",
    "risk_level",
    "status",
    "action",
]
