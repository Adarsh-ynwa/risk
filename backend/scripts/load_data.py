"""Load CSV transactions into SQLite and run initial risk analysis on a sample."""

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import desc
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models.db_models import Transaction
from app.services.ml_service import ml_service
from app.services.transaction_service import analyze_transaction

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bank_fraud.csv"


def load_demo_rows() -> pd.DataFrame:
    """Find appended synthetic fraud scenarios even when the source CSV is very large."""
    matching = []
    for chunk in pd.read_csv(DATA_PATH, chunksize=100_000):
        rows = chunk[chunk["transaction_id"].astype(str).str.startswith("DEMOHR")]
        if not rows.empty:
            matching.append(rows)
    return pd.concat(matching, ignore_index=True) if matching else pd.DataFrame()


def load_csv_to_db(db: Session, max_rows: int | None = None, force_reload: bool = False):
    if not DATA_PATH.exists():
        print(f"Dataset not found at {DATA_PATH}")
        sys.exit(1)

    max_rows = max_rows or settings.max_transactions_load
    print(f"Loading up to {max_rows} rows...")
    demo_df = load_demo_rows()
    base_rows = max(0, max_rows - len(demo_df))
    base_df = pd.read_csv(DATA_PATH, nrows=base_rows)
    df = pd.concat([base_df, demo_df], ignore_index=True)

    existing = db.query(Transaction).count()
    if existing >= len(df) and not force_reload:
        print(f"Database already has {existing} transactions. Skipping load.")
        return

    db.query(Transaction).delete()
    db.commit()

    # The CSV already matches the database columns. Bulk mappings avoid creating
    # one SQLAlchemy object per row, keeping a 150k+ row reload fast and memory-safe.
    df["status"] = "PENDING"
    df["fraud_type"] = df["fraud_type"].where(df["fraud_type"].notna(), None)
    records = df.to_dict(orient="records")
    loaded_count = len(records)
    batch_size = 5_000
    for start in range(0, loaded_count, batch_size):
        db.bulk_insert_mappings(Transaction, records[start:start + batch_size])
    db.commit()
    records.clear()
    print(f"Loaded {loaded_count} transactions.")


def analyze_high_risk_sample(db: Session, target: int = 5000):
    """Pre-analyze fraud cases, high-signal transactions, and top amounts for demo."""
    ml_service.load()

    fraud_ids = [
        transaction_id
        for (transaction_id,) in db.query(Transaction.transaction_id)
        .filter(Transaction.is_fraud == True)  # noqa: E712
        .all()
    ]
    high_signal_ids = [
        transaction_id
        for (transaction_id,) in db.query(Transaction.transaction_id)
        .filter(
            Transaction.is_fraud == False,  # noqa: E712
            (Transaction.is_international == True)  # noqa: E712
            | (Transaction.failed_attempts >= 2)
            | (Transaction.is_night_transaction == True)  # noqa: E712
            | (Transaction.pin_changed_recently == True),  # noqa: E712
        )
        .limit(2000)
        .all()
    ]
    high_amount_ids = [
        transaction_id
        for (transaction_id,) in db.query(Transaction.transaction_id)
        .filter(Transaction.is_fraud == False)  # noqa: E712
        .order_by(desc(Transaction.transaction_amount))
        .limit(2000)
        .all()
    ]

    seen = set()
    candidates = []
    for transaction_id in fraud_ids + high_signal_ids + high_amount_ids:
        if transaction_id not in seen:
            seen.add(transaction_id)
            candidates.append(transaction_id)
        if len(candidates) >= target:
            break

    count = 0
    for transaction_id in candidates:
        try:
            analyze_transaction(db, transaction_id)
            count += 1
        except Exception as e:
            print(f"  Skip {transaction_id}: {e}")
    print(f"Pre-analyzed {count} new transactions ({len(candidates)} candidates).")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force-reload", action="store_true", help="Reload CSV even if DB populated")
    parser.add_argument("--analyze-only", action="store_true", help="Only run risk analysis on existing DB")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not args.analyze_only:
            load_csv_to_db(db, force_reload=args.force_reload)
        ml_service.load()
        analyze_high_risk_sample(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
