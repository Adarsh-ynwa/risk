"""Append labeled high-risk demo payments to the training CSV and local SQLite database."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.db_models import Transaction

BACKEND_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BACKEND_DIR / "data" / "bank_fraud.csv"


def make_row(number: int) -> dict:
    """Create a labeled synthetic account-takeover payment for model training."""
    now = datetime.now()
    critical = number % 2 == 0
    balance = 75_000 if critical else 45_000
    return {
        "transaction_id": f"DEMOHR{uuid4().hex[:14].upper()}",
        "customer_id": f"DEMO-HIGH-RISK-{number:05d}",
        "transaction_date": now.date().isoformat(),
        "transaction_time": "02:15:00" if critical else "03:40:00",
        "hour_of_day": 2 if critical else 3,
        "is_weekend": 1,
        "is_night_transaction": 1,
        "country": "India",
        "city": "Mumbai",
        "merchant_category": "Crypto Exchange" if critical else "Online Shopping",
        "payment_method": "Bank Transfer",
        "device_type": "Mobile",
        "customer_age": 23,
        "credit_score": 480,
        "account_age_years": 0.4 if critical else 0.8,
        "account_balance": balance,
        "transaction_amount": 68_000 if critical else 30_000,
        "num_prev_transactions": 8,
        "transaction_freq_monthly": 75 if critical else 45,
        "distance_from_home_km": 850 if critical else 320,
        "time_since_last_txn_hrs": 0.03,
        "is_international": 1,
        "failed_attempts": 6 if critical else 3,
        "pin_changed_recently": 1,
        "is_fraud": 1,
        "fraud_type": "Synthetic account takeover",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000, help="Number of labeled high-risk records to add")
    args = parser.parse_args()
    if args.count < 1:
        raise ValueError("--count must be at least 1")

    rows = [make_row(i + 1) for i in range(args.count)]
    pd.DataFrame(rows).to_csv(CSV_PATH, mode="a", header=False, index=False)

    db = SessionLocal()
    try:
        db.add_all([
            Transaction(
                **{**row, "is_weekend": bool(row["is_weekend"]), "is_night_transaction": bool(row["is_night_transaction"]),
                   "is_international": bool(row["is_international"]), "pin_changed_recently": bool(row["pin_changed_recently"]),
                   "is_fraud": bool(row["is_fraud"]), "status": "PENDING"}
            )
            for row in rows
        ])
        db.commit()
    finally:
        db.close()

    print(f"Added {args.count} labeled high-risk demo records to {CSV_PATH.name} and airisk.db.")
    print("Next: retrain the model, then reload the database with --force-reload.")


if __name__ == "__main__":
    main()
