"""Train XGBoost fraud detection model and save artifacts."""

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.feature_engineering import (
    BASE_NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    add_engineered_features,
    ENGINEERED_FEATURE_NAMES,
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bank_fraud.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
SAMPLE_SIZE = 200000


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        print("Dataset not found. Run generate_sample_data.py first.")
        sys.exit(1)
    print(f"Loading up to {SAMPLE_SIZE} rows from {DATA_PATH}...")
    demo_chunks = []
    for chunk in pd.read_csv(DATA_PATH, chunksize=100_000):
        demo_rows = chunk[chunk["transaction_id"].astype(str).str.startswith("DEMOHR")]
        if not demo_rows.empty:
            demo_chunks.append(demo_rows)
    demo_df = pd.concat(demo_chunks, ignore_index=True) if demo_chunks else pd.DataFrame()
    base_df = pd.read_csv(DATA_PATH, nrows=max(0, SAMPLE_SIZE - len(demo_df)))
    df = pd.concat([base_df, demo_df], ignore_index=True)
    print(f"Included {len(demo_df)} synthetic high-risk training records.")
    return clean_data(df)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values before training."""
    out = df.copy()
    exclude = {"transaction_id", "customer_id", "transaction_date", "transaction_time", "is_fraud", "fraud_type"}
    cat_cols = [c for c in CATEGORICAL_FEATURES if c in out.columns]
    num_cols = [c for c in out.select_dtypes(include=[np.number]).columns if c not in exclude]

    for col in num_cols:
        out[col] = out[col].fillna(out[col].median())
    for col in cat_cols:
        out[col] = out[col].fillna("Unknown")
    for col in ["is_weekend", "is_night_transaction", "is_international", "pin_changed_recently"]:
        if col in out.columns:
            out[col] = out[col].fillna(False).astype(bool)
    if "is_fraud" in out.columns:
        out["is_fraud"] = out["is_fraud"].fillna(0).astype(int)
    return out


def build_preprocessor(feature_cols: list[str], cat_cols: list[str], num_cols: list[str]):
    transformers = []
    if num_cols:
        transformers.append(("num", StandardScaler(), num_cols))
    if cat_cols:
        transformers.append(
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    df = add_engineered_features(df)

    target = "is_fraud"
    exclude = {"transaction_id", "customer_id", "transaction_date", "transaction_time", "is_fraud", "fraud_type"}
    feature_cols = [c for c in df.columns if c not in exclude]

    cat_cols = [c for c in CATEGORICAL_FEATURES if c in feature_cols]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X = df[feature_cols]
    y = df[target].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    preprocessor = build_preprocessor(feature_cols, cat_cols, num_cols)

    pos = y_train.sum()
    neg = len(y_train) - pos
    scale_pos_weight = neg / max(pos, 1)

    model_type = "XGBoost"
    try:
        from xgboost import XGBClassifier

        clf = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    except ImportError:
        from sklearn.ensemble import RandomForestClassifier

        model_type = "RandomForest"
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )

    print(f"Training {model_type}...")
    preprocessor.fit(X_train)
    X_train_t = preprocessor.transform(X_train)
    X_test_t = preprocessor.transform(X_test)
    clf.fit(X_train_t, y_train)

    y_pred = clf.predict(X_test_t)
    y_proba = clf.predict_proba(X_test_t)[:, 1]

    metrics = {
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "pr_auc": float(average_precision_score(y_test, y_proba)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "trained_at": datetime.utcnow().isoformat(),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "fraud_rate": float(y.mean()),
    }

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    print(f"ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"PR-AUC: {metrics['pr_auc']:.4f}")

    joblib.dump(clf, ARTIFACTS_DIR / "model.joblib")
    joblib.dump(preprocessor, ARTIFACTS_DIR / "preprocessor.joblib")

    metadata = {
        "feature_names": feature_cols,
        "categorical_features": cat_cols,
        "numeric_features": num_cols,
        "engineered_features": ENGINEERED_FEATURE_NAMES,
        "model_type": model_type,
    }
    with open(ARTIFACTS_DIR / "feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open(ARTIFACTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nArtifacts saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
