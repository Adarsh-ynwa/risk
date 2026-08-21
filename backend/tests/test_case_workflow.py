import sys
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base
from app.models.db_models import Transaction
from app.services.transaction_service import (
    apply_action,
    create_verification,
    get_case_timeline,
    get_customer_behavior,
    request_unblock,
    review_unblock,
    resolve_verification,
)


def transaction(transaction_id: str, date: str, amount: float, **overrides) -> Transaction:
    values = {
        "transaction_id": transaction_id,
        "customer_id": "CUST-TEST",
        "transaction_date": date,
        "transaction_time": "12:00:00",
        "hour_of_day": 12,
        "is_weekend": False,
        "is_night_transaction": False,
        "country": "India",
        "city": "Mumbai",
        "merchant_category": "Groceries",
        "payment_method": "UPI",
        "device_type": "Mobile",
        "customer_age": 30,
        "credit_score": 700,
        "account_age_years": 3,
        "account_balance": 100000,
        "transaction_amount": amount,
        "num_prev_transactions": 10,
        "transaction_freq_monthly": 5,
        "distance_from_home_km": 2,
        "time_since_last_txn_hrs": 24,
        "is_international": False,
        "failed_attempts": 0,
        "pin_changed_recently": False,
        "is_fraud": False,
        "status": "ANALYZED",
    }
    values.update(overrides)
    return Transaction(**values)


class CaseWorkflowTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        self.db = sessionmaker(bind=engine)()
        self.db.add(transaction("TXN-OLD", "2026-01-01", 1000))
        self.db.add(transaction("TXN-NEW", "2026-01-02", 10000, country="UAE", city="Dubai", device_type="Desktop"))
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_behavior_verification_and_timeline(self):
        behavior = get_customer_behavior(self.db, "TXN-NEW")
        self.assertEqual(behavior.history_count, 1)
        self.assertEqual(behavior.amount_ratio_to_median, 10)
        self.assertTrue(behavior.is_new_country)

        verification = create_verification(self.db, "TXN-NEW", "OTP", "Test Analyst", None)
        self.assertEqual(verification.status, "PENDING")
        resolved = resolve_verification(self.db, verification.id, "PASSED", "Test Analyst", "OTP matched")
        self.assertEqual(resolved.status, "PASSED")

        timeline = get_case_timeline(self.db, "TXN-NEW")
        event_types = {event.event_type for event in timeline}
        self.assertIn("VERIFICATION", event_types)
        self.assertIn("VERIFICATION_RESULT", event_types)
        self.assertIn("ACTION", event_types)

    def test_block_is_terminal_for_verification_and_actions(self):
        apply_action(self.db, "TXN-NEW", "BLOCK")
        with self.assertRaisesRegex(ValueError, "terminal"):
            apply_action(self.db, "TXN-NEW", "APPROVE")
        with self.assertRaisesRegex(ValueError, "cannot enter verification"):
            create_verification(self.db, "TXN-NEW", "OTP", "Test Analyst", None)

        request = request_unblock(self.db, "TXN-NEW", "Customer proved the original block was mistaken", "Test Analyst")
        self.assertEqual(request.status, "PENDING")
        with self.assertRaisesRegex(ValueError, "cannot enter verification"):
            create_verification(self.db, "TXN-NEW", "OTP", "Test Analyst", None)

        reviewed = review_unblock(self.db, request.id, "APPROVE", "Senior Analyst", "Evidence reviewed")
        self.assertEqual(reviewed.status, "APPROVED")
        verification = create_verification(self.db, "TXN-NEW", "OTP", "Test Analyst", None)
        self.assertEqual(verification.status, "PENDING")


if __name__ == "__main__":
    unittest.main()
