"""
Inference-time prediction service. Loads the serialized preprocessor and
models once, then exposes a single `predict_claim` function that both the
FastAPI app and any batch/CLI tooling can reuse.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import joblib
import pandas as pd

from src import config
from src.preprocessing import clean_data, split_features_target

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class FraudModelService:
    """Wraps the trained artifacts and exposes a simple predict() API."""

    def __init__(self):
        logger.info("Loading model artifacts from %s", config.MODELS_DIR)
        self.preprocessor = joblib.load(config.PREPROCESSOR_PATH)
        self.xgb_model = joblib.load(config.XGB_MODEL_PATH)
        self.iso_forest = joblib.load(config.ISOFOREST_MODEL_PATH)
        self.threshold = config.DECISION_THRESHOLD

    def _to_dataframe(self, claim: dict[str, Any]) -> pd.DataFrame:
        return pd.DataFrame([claim])

    def predict(self, claim: dict[str, Any]) -> dict[str, Any]:
        """
        Score a single claim (as a dict of raw field -> value, matching the
        original CSV schema) and return fraud probability, label, risk level,
        and the Isolation Forest anomaly flag.
        """
        df = self._to_dataframe(claim)
        df = clean_data(df)
        X, _ = split_features_target(df)
        X_transformed = self.preprocessor.transform(X)

        fraud_probability = float(self.xgb_model.predict_proba(X_transformed)[:, 1][0])
        fraud_label = "fraud" if fraud_probability >= self.threshold else "not_fraud"
        risk_level = self._risk_level(fraud_probability)

        anomaly_raw = int(self.iso_forest.predict(X_transformed)[0])  # 1 normal, -1 anomaly
        is_anomaly = anomaly_raw == -1

        return {
            "fraud_probability": round(fraud_probability, 4),
            "fraud_label": fraud_label,
            "risk_level": risk_level,
            "is_anomaly": is_anomaly,
        }

    @staticmethod
    def _risk_level(probability: float) -> str:
        if probability >= 0.75:
            return "high"
        if probability >= 0.4:
            return "medium"
        return "low"


@lru_cache(maxsize=1)
def get_model_service() -> "FraudModelService":
    """Singleton accessor so models are loaded into memory exactly once."""
    return FraudModelService()
