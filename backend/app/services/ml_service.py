"""ML model loading and inference service."""

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config import ARTIFACTS_DIR, settings
from app.services.feature_engineering import add_engineered_features


class MLService:
    def __init__(self):
        self.model = None
        self.preprocessor = None
        self.feature_names: list[str] = []
        self.metrics: dict[str, Any] = {}
        self.model_type = settings.model_name
        self._loaded = False

    def load(self) -> bool:
        model_path = ARTIFACTS_DIR / "model.joblib"
        preprocessor_path = ARTIFACTS_DIR / "preprocessor.joblib"
        metadata_path = ARTIFACTS_DIR / "feature_metadata.json"
        metrics_path = ARTIFACTS_DIR / "metrics.json"

        if not model_path.exists() or not preprocessor_path.exists():
            return False

        self.model = joblib.load(model_path)
        self.preprocessor = joblib.load(preprocessor_path)

        if metadata_path.exists():
            with open(metadata_path) as f:
                meta = json.load(f)
                self.feature_names = meta.get("feature_names", [])
                self.model_type = meta.get("model_type", self.model_type)

        if metrics_path.exists():
            with open(metrics_path) as f:
                self.metrics = json.load(f)

        self._loaded = True
        return True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def predict_fraud_probability(self, transaction: dict[str, Any]) -> float:
        if not self._loaded:
            return self._heuristic_probability(transaction)

        df = pd.DataFrame([transaction])
        df = add_engineered_features(df)
        if self.feature_names:
            cols = [c for c in self.feature_names if c in df.columns]
            df = df[cols]
        X = self.preprocessor.transform(df)
        proba = self.model.predict_proba(X)[0]
        fraud_idx = 1 if len(proba) > 1 else 0
        return float(proba[fraud_idx])

    def _heuristic_probability(self, txn: dict[str, Any]) -> float:
        """Fallback when model not trained — uses rule-like signals."""
        score = 0.0
        if txn.get("is_international"):
            score += 0.15
        if txn.get("is_night_transaction"):
            score += 0.10
        if int(txn.get("failed_attempts", 0)) >= 2:
            score += 0.20
        if txn.get("pin_changed_recently"):
            score += 0.10
        amount = float(txn.get("transaction_amount", 0))
        balance = float(txn.get("account_balance", 1))
        if amount > balance * 0.5:
            score += 0.20
        if float(txn.get("distance_from_home_km", 0)) > 200:
            score += 0.15
        return min(score, 0.95)


ml_service = MLService()
