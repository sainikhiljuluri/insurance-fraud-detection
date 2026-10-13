"""
Evaluation utilities: standard classification metrics plus confusion
matrix / ROC / precision-recall artifacts used in the project report.
"""
from __future__ import annotations

import logging

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def evaluate_classifier(model, X_test, y_test, threshold: float = 0.5) -> dict:
    """Compute standard classification metrics for a fitted probabilistic classifier."""
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "false_positive_rate": float(false_positive_rate),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "threshold": threshold,
    }

    logger.info("\n%s", classification_report(y_test, y_pred, target_names=["legitimate", "fraud"]))
    return metrics


def evaluate_at_multiple_thresholds(model, X_test, y_test, thresholds=None) -> list:
    """Sweep decision thresholds to help pick an operating point (precision/recall tradeoff)."""
    if thresholds is None:
        thresholds = np.arange(0.1, 0.95, 0.05)
    results = []
    for t in thresholds:
        m = evaluate_classifier(model, X_test, y_test, threshold=float(t))
        results.append(m)
    return results
