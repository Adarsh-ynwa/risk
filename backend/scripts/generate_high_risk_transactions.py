"""Append labeled high-risk demo payments to the training CSV and local SQLite database."""

import argparse
import random
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
    """Create a varied synthetic account-takeover payment for demos."""
    now = datetime.now()
    rng = random.Random(number * 7919)
    balance = round(rng.uniform(35_000, 140_000), 2)
    amount = round(balance * rng.uniform(0.18, 0.88), 2)
    international = rng.random() < 0.46
    night = rng.random() < 0.52
    hour = rng.choice([0, 1, 2, 3, 4, 22, 23]) if night else rng.randint(7, 21)
    distance = round(rng.uniform(20, 750), 2)
    return {
        "transaction_id": f"DEMOHR{uuid4().hex[:14].upper()}",
        "customer_id": f"DEMO-HIGH-RISK-{number:05d}",
        "transaction_date": now.date().isoformat(),
        "transaction_time": f"{hour:02d}:{rng.randint(0, 59):02d}:00",
        "hour_of_day": hour,
        "is_weekend": int(rng.random() < 0.45),
        "is_night_transaction": int(night),
        "country": rng.choice(["UAE", "Singapore", "UK", "USA"]) if international else "India",
        "city": rng.choice(["Dubai", "Singapore", "London", "New York"]) if international else rng.choice(["Mumbai", "Delhi", "Bangalore"]),
        "merchant_category": rng.choice(["Crypto Exchange", "Electronics", "Travel", "Online Services"]),
        "payment_method": rng.choice(["Bank Transfer", "Credit Card", "Wallet", "UPI"]),
        "device_type": rng.choice(["Mobile", "Desktop", "Tablet"]),
        "customer_age": rng.randint(20, 61),
        "credit_score": rng.randint(410, 710),
        "account_age_years": round(rng.uniform(0.3, 5), 2),
        "account_balance": balance,
        "transaction_amount": amount,
        "num_prev_transactions": rng.randint(3, 80),
        "transaction_freq_monthly": round(rng.uniform(8, 58), 2),
        "distance_from_home_km": distance,
        "time_since_last_txn_hrs": round(rng.uniform(0.03, 8), 2),
        "is_international": int(international),
        "failed_attempts": rng.randint(0, 5),
        "pin_changed_recently": int(rng.random() < 0.40),
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
