"""Refresh existing demo transactions with varied, realistic risk signals and rescore them."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.db_models import Transaction
from app.services.ml_service import ml_service
from app.services.transaction_service import analyze_transaction
from scripts.generate_high_risk_transactions import CSV_PATH, make_row


def main() -> None:
    db = SessionLocal()
    try:
        transactions = (
            db.query(Transaction)
            .filter(Transaction.transaction_id.like("DEMOHR%"))
            .order_by(Transaction.id)
            .all()
        )
        if not transactions:
            print("No DEMOHR transactions found.")
            return
        ml_service.load()
        refreshed_rows = []
        for number, txn in enumerate(transactions, start=1):
            varied = make_row(number)
            varied["transaction_id"] = txn.transaction_id
            varied["customer_id"] = txn.customer_id
            refreshed_rows.append(varied)
            for field, value in varied.items():
                if field not in {"transaction_id", "customer_id", "is_fraud", "fraud_type"}:
                    setattr(txn, field, value)
            txn.is_fraud = True
            txn.fraud_type = "Synthetic account takeover"
            txn.risk_score = None
            txn.risk_level = None
            txn.status = "PENDING"
            txn.action = None
        db.commit()
        for txn in transactions:
            analyze_transaction(db, txn.transaction_id)

        csv = pd.read_csv(CSV_PATH)
        for column in ["account_age_years", "transaction_freq_monthly", "time_since_last_txn_hrs"]:
            csv[column] = csv[column].astype(float)
        demo_indexes = csv.index[csv["transaction_id"].astype(str).str.startswith("DEMOHR")]
        by_id = {row["transaction_id"]: row for row in refreshed_rows}
        for index in demo_indexes:
            transaction_id = str(csv.at[index, "transaction_id"])
            if transaction_id in by_id:
                for field, value in by_id[transaction_id].items():
                    if field in csv.columns:
                        csv.at[index, field] = value
        csv.to_csv(CSV_PATH, index=False)
        scores = [txn.risk_score for txn in transactions]
        print(f"Refreshed and rescored {len(transactions)} demo transactions.")
        print(f"Score range: {min(scores):.2f}–{max(scores):.2f}; unique scores: {len(set(scores))}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
