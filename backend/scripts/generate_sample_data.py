"""Generate synthetic bank fraud dataset for development/demo."""

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bank_fraud.csv"
NUM_ROWS = 150000

COUNTRIES = ["India", "USA", "UK", "UAE", "Singapore", "Germany", "Australia"]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Dubai", "London", "New York"]
MERCHANTS = ["Electronics", "Groceries", "Travel", "Fashion", "Food", "Healthcare", "Entertainment", "Fuel", "Online Services"]
PAYMENTS = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Wallet"]
DEVICES = ["Mobile", "Desktop", "Tablet"]
FRAUD_TYPES = ["Card Not Present", "Account Takeover", "Identity Theft", "Merchant Fraud", "None"]


def generate_row(i: int) -> dict:
    is_fraud = random.random() < 0.04
    is_international = random.random() < (0.25 if is_fraud else 0.08)
    is_night = random.random() < (0.35 if is_fraud else 0.12)
    failed = random.randint(0, 5) if is_fraud else random.randint(0, 1)
    pin_changed = random.random() < (0.3 if is_fraud else 0.05)
    balance = round(random.uniform(5000, 500000), 2)
    amount = round(random.uniform(500, 150000 if is_fraud else 50000), 2)
    distance = round(random.uniform(0, 800 if is_fraud else 100), 2)
    account_age = round(random.uniform(0.1, 15), 2)

    date = datetime(2024, 1, 1) + timedelta(days=random.randint(0, 365))
    hour = random.randint(0, 23)

    return {
        "transaction_id": f"TXN{i:010d}",
        "customer_id": f"CUST{random.randint(1, 20000):06d}",
        "transaction_date": date.strftime("%Y-%m-%d"),
        "transaction_time": f"{hour:02d}:{random.randint(0,59):02d}",
        "hour_of_day": hour,
        "is_weekend": date.weekday() >= 5,
        "is_night_transaction": is_night or hour >= 22 or hour <= 6,
        "country": random.choice(COUNTRIES) if is_international else "India",
        "city": random.choice(CITIES),
        "merchant_category": random.choice(MERCHANTS),
        "payment_method": random.choice(PAYMENTS),
        "device_type": random.choice(DEVICES),
        "customer_age": random.randint(18, 70),
        "credit_score": random.randint(300, 850),
        "account_age_years": account_age,
        "account_balance": balance,
        "transaction_amount": amount,
        "num_prev_transactions": random.randint(0, 500),
        "transaction_freq_monthly": round(random.uniform(1, 60 if is_fraud else 25), 2),
        "distance_from_home_km": distance,
        "time_since_last_txn_hrs": round(random.uniform(0.1, 720), 2),
        "is_international": is_international,
        "failed_attempts": failed,
        "pin_changed_recently": pin_changed,
        "is_fraud": is_fraud,
        "fraud_type": random.choice(FRAUD_TYPES[:-1]) if is_fraud else "None",
    }


def main():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Generating {NUM_ROWS} synthetic transactions...")
    rows = [generate_row(i + 1) for i in range(NUM_ROWS)]
    df = pd.DataFrame(rows)
    df.to_csv(DATA_PATH, index=False)
    print(f"Saved to {DATA_PATH}")
    print(f"Fraud rate: {df['is_fraud'].mean():.4f}")


if __name__ == "__main__":
    main()
