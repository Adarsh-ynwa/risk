"""Train XGBoost fraud detection model and save artifacts."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.feature_engineering import (
    BASE_NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    add_engineered_features,
    ENGINEERED_FEATURE_NAMES,
)
from app.services.risk_engine import compute_risk

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "bank_fraud.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"
SAMPLE_SIZE = 200000
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15

# Transparent scenario assumptions for cost-sensitive threshold selection.
# Override these values for a merchant's actual economics.
FALSE_POSITIVE_COST_INR = 200.0
FALSE_NEGATIVE_COST_INR = 5500.0


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        print("Dataset not found. Run generate_sample_data.py first.")
        sys.exit(1)
    print(f"Loading up to {SAMPLE_SIZE} rows from {DATA_PATH}...")
    chunks = []
    rows_remaining = SAMPLE_SIZE
    excluded_demo_rows = 0
    for chunk in pd.read_csv(DATA_PATH, chunksize=100_000):
        demo_mask = chunk["transaction_id"].astype(str).str.startswith("DEMOHR")
        excluded_demo_rows += int(demo_mask.sum())
        eligible = chunk.loc[~demo_mask]
        if rows_remaining > 0:
            selected = eligible.head(rows_remaining)
            chunks.append(selected)
            rows_remaining -= len(selected)
        if rows_remaining == 0:
            break
    df = pd.concat(chunks, ignore_index=True)
    print(f"Excluded {excluded_demo_rows} demo-only records from model development.")
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


def chronological_split(df: pd.DataFrame):
    """Create train/validation/test sets in time order with an untouched test tail."""
    ordered = df.assign(
        _event_time=pd.to_datetime(
            df["transaction_date"].astype(str) + " " + df["transaction_time"].astype(str),
            errors="coerce",
        )
    ).sort_values(["_event_time", "transaction_id"], kind="stable")
    ordered = ordered.drop(columns="_event_time")
    train_end = int(len(ordered) * (1 - VALIDATION_FRACTION - TEST_FRACTION))
    validation_end = int(len(ordered) * (1 - TEST_FRACTION))
    return ordered.iloc[:train_end], ordered.iloc[train_end:validation_end], ordered.iloc[validation_end:]


def metrics_at_threshold(y_true, probabilities, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    false_positive_cost = float(fp * FALSE_POSITIVE_COST_INR)
    false_negative_cost = float(fn * FALSE_NEGATIVE_COST_INR)
    return {
        "threshold": round(float(threshold), 4),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        "alert_rate": float(predictions.mean()),
        "false_positive_cost_inr": false_positive_cost,
        "false_negative_cost_inr": false_negative_cost,
        "estimated_total_cost_inr": false_positive_cost + false_negative_cost,
    }


def select_cost_threshold(y_true, probabilities) -> tuple[float, list[dict]]:
    candidates = np.round(np.arange(0.05, 0.951, 0.01), 2)
    results = [metrics_at_threshold(y_true, probabilities, threshold) for threshold in candidates]
    best = min(results, key=lambda item: (item["estimated_total_cost_inr"], -item["recall"]))
    display_thresholds = sorted({0.3, 0.5, 0.7, float(best["threshold"])})
    comparison = [metrics_at_threshold(y_true, probabilities, threshold) for threshold in display_thresholds]
    return float(best["threshold"]), comparison


def evaluate_deployed_hybrid_system(test_features: pd.DataFrame, y_true, probabilities) -> dict:
    """Evaluate the deployed ML-plus-rules HIGH/CRITICAL alert boundary."""
    hybrid_scores = np.array([
        compute_risk(row.to_dict(), float(probability))["final_risk_score"] / 100.0
        for (_, row), probability in zip(test_features.iterrows(), probabilities)
    ])
    return metrics_at_threshold(y_true, hybrid_scores, 0.60)


def main():
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_data()
    df = add_engineered_features(df)
    train_df, validation_df, test_df = chronological_split(df)

    target = "is_fraud"
    exclude = {"transaction_id", "customer_id", "transaction_date", "transaction_time", "is_fraud", "fraud_type"}
    feature_cols = [c for c in df.columns if c not in exclude]

    cat_cols = [c for c in CATEGORICAL_FEATURES if c in feature_cols]
    num_cols = [c for c in feature_cols if c not in cat_cols]

    X_train, y_train = train_df[feature_cols], train_df[target].astype(int)
    X_validation, y_validation = validation_df[feature_cols], validation_df[target].astype(int)
    X_test, y_test = test_df[feature_cols], test_df[target].astype(int)
    print(f"Chronological split: train={len(train_df)}, validation={len(validation_df)}, test={len(test_df)}")

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
    X_validation_t = preprocessor.transform(X_validation)
    X_test_t = preprocessor.transform(X_test)
    clf.fit(X_train_t, y_train)

    validation_proba = clf.predict_proba(X_validation_t)[:, 1]
    selected_threshold, validation_comparison = select_cost_threshold(y_validation, validation_proba)
    y_proba = clf.predict_proba(X_test_t)[:, 1]
    selected_metrics = metrics_at_threshold(y_test, y_proba, selected_threshold)
    hybrid_test_metrics = evaluate_deployed_hybrid_system(X_test, y_test, y_proba)

    metrics = {
        **selected_metrics,
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "pr_auc": float(average_precision_score(y_test, y_proba)),
        "trained_at": datetime.now(UTC).isoformat(),
        "train_size": len(X_train),
        "validation_size": len(X_validation),
        "test_size": len(X_test),
        "fraud_rate": float(df[target].mean()),
        "split_strategy": "chronological_70_15_15",
        "threshold_selected_on": "validation_set_only",
        "cost_assumptions_inr": {
            "false_positive": FALSE_POSITIVE_COST_INR,
            "false_negative": FALSE_NEGATIVE_COST_INR,
        },
        "validation_threshold_comparison": validation_comparison,
        "hybrid_test_metrics": hybrid_test_metrics,
    }

    print(f"\nSelected threshold on validation data: {selected_threshold:.2f}")
    print(f"Test precision: {metrics['precision']:.4f}")
    print(f"Test recall: {metrics['recall']:.4f}")
    print(f"Test false positives: {metrics['false_positives']}")
    print(f"Test false negatives: {metrics['false_negatives']}")
    print(f"Test estimated cost: INR {metrics['estimated_total_cost_inr']:,.0f}")
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
        "decision_threshold": selected_threshold,
    }
    with open(ARTIFACTS_DIR / "feature_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    with open(ARTIFACTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nArtifacts saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
