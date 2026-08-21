"""Idempotently seed an empty deployed database with a compact fraud demo dataset."""

import os
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models.db_models import Transaction
from app.services.ml_service import ml_service
from app.services.transaction_service import analyze_transaction
from scripts.generate_high_risk_transactions import make_row
from scripts.generate_sample_data import generate_row

BASE_ROWS = 160
RISK_DEMO_ROWS = 80


def to_transaction(row: dict) -> Transaction:
    values = row.copy()
    for field in ["is_weekend", "is_night_transaction", "is_international", "pin_changed_recently", "is_fraud"]:
        values[field] = bool(values[field])
    values["status"] = "PENDING"
    return Transaction(**values)


def main() -> None:
    if os.getenv("SEED_DEMO_DATA", "false").lower() not in {"1", "true", "yes"}:
        print("Production demo seeding disabled.")
        return

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Transaction).count()
        if existing:
            print(f"Database already contains {existing} transactions; seed skipped.")
            return

        random.seed(42)
        np.random.seed(42)
        rows = [generate_row(i + 1) for i in range(BASE_ROWS)]
        rows.extend(make_row(i + 1) for i in range(RISK_DEMO_ROWS))
        db.add_all([to_transaction(row) for row in rows])
        db.commit()

        if not ml_service.load():
            raise RuntimeError("Model artifacts are unavailable; cannot score seed data")
        transaction_ids = [row["transaction_id"] for row in rows]
        for index, transaction_id in enumerate(transaction_ids, start=1):
            analyze_transaction(db, transaction_id)
            if index % 50 == 0:
                print(f"Analyzed {index}/{len(transaction_ids)} seed transactions.")
        print(f"Seeded and analyzed {len(transaction_ids)} demo transactions.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
