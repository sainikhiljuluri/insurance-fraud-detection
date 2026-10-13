"""
Trains the fraud detection models:
  - XGBoost classifier (supervised) for fraud probability scoring
  - Isolation Forest (unsupervised) for anomaly-based fraud signal

Serializes the trained models, the fitted preprocessor, and feature
metadata to the models/ directory so they can be loaded by the FastAPI
inference service without retraining.

Usage:
    python -m src.train
"""
from __future__ import annotations

import json
import logging

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from src import config
from src.preprocessing import prepare_training_data
from src.evaluate import evaluate_classifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train_xgboost(X_train, y_train) -> XGBClassifier:
    logger.info("Training XGBoost classifier with params: %s", config.XGB_PARAMS)
    model = XGBClassifier(**config.XGB_PARAMS)
    model.fit(X_train, y_train)
    return model


def train_isolation_forest(X_train) -> IsolationForest:
    logger.info("Training Isolation Forest with params: %s", config.ISOLATION_FOREST_PARAMS)
    model = IsolationForest(**config.ISOLATION_FOREST_PARAMS)
    model.fit(X_train)
    return model


def main():
    # 1. Load + preprocess
    X, y, preprocessor, feature_names, numeric_cols, categorical_cols = prepare_training_data()

    # 2. Train / validation split (stratified on the fraud label)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=config.TEST_SIZE,
        random_state=config.RANDOM_STATE,
        stratify=y,
    )
    logger.info("Train shape: %s | Test shape: %s", X_train.shape, X_test.shape)
    logger.info("Fraud rate — train: %.3f | test: %.3f", y_train.mean(), y_test.mean())

    # 3. Train models
    xgb_model = train_xgboost(X_train, y_train)
    iso_forest = train_isolation_forest(X_train)

    # 4. Evaluate
    metrics = evaluate_classifier(xgb_model, X_test, y_test, threshold=config.DECISION_THRESHOLD)
    logger.info("Evaluation metrics: %s", json.dumps(metrics, indent=2))
    
    from src.evaluate import evaluate_at_multiple_thresholds

    sweep_results = evaluate_at_multiple_thresholds(xgb_model, X_test, y_test)
    print("\n--- THRESHOLD SWEEP ---")
    for r in sweep_results:
        print(f"threshold={r['threshold']:.2f}  recall={r['recall']:.3f}  precision={r['precision']:.3f}")
    print("--- END SWEEP ---\n")

    # Isolation Forest agreement rate: how often the anomaly flag agrees
    # with the ground-truth fraud label (informational, not a classifier metric).
    iso_pred_raw = iso_forest.predict(X_test)  # 1 = normal, -1 = anomaly
    iso_pred_fraud = (iso_pred_raw == -1).astype(int)
    agreement = float(np.mean(iso_pred_fraud == y_test.values))
    metrics["isolation_forest_agreement_with_labels"] = agreement
    logger.info("Isolation Forest agreement with true labels: %.3f", agreement)

    # 5. Persist artifacts
    joblib.dump(xgb_model, config.XGB_MODEL_PATH)
    joblib.dump(iso_forest, config.ISOFOREST_MODEL_PATH)
    joblib.dump(preprocessor, config.PREPROCESSOR_PATH)

    feature_metadata = {
        "feature_names": feature_names,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "n_features": len(feature_names),
        "decision_threshold": config.DECISION_THRESHOLD,
    }
    with open(config.FEATURE_METADATA_PATH, "w") as f:
        json.dump(feature_metadata, f, indent=2)

    with open(config.METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Saved model artifacts to %s", config.MODELS_DIR)
    logger.info("Saved metrics to %s", config.METRICS_PATH)

    return metrics


if __name__ == "__main__":
    main()
