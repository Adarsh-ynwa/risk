"""Inspect the bank fraud dataset."""

import sys
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bank_fraud.csv"


def main():
    if not DATA_PATH.exists():
        print(f"Dataset not found at {DATA_PATH}")
        print("Place bank_fraud.csv in backend/data/ or run generate_sample_data.py")
        sys.exit(1)

    print(f"Loading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, nrows=5000)
    print(f"\nShape (sample): {df.shape}")
    print(f"\nColumns:\n{df.columns.tolist()}")
    print(f"\nDtypes:\n{df.dtypes}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    print(f"\nFraud rate: {df['is_fraud'].mean():.4f}")
    print(f"\nFraud type distribution:\n{df['fraud_type'].value_counts(dropna=False).head(10)}")
    print(f"\nNumeric summary:\n{df.describe().T.head(15)}")
    print(f"\nCategorical samples:")
    for col in ["country", "merchant_category", "payment_method", "device_type"]:
        if col in df.columns:
            print(f"  {col}: {df[col].nunique()} unique — {df[col].value_counts().head(3).to_dict()}")


if __name__ == "__main__":
    main()
