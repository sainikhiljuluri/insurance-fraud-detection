"""
Central configuration for the Insurance Claims Fraud Detection System.
All paths, model hyperparameters, and environment settings live here so
the rest of the codebase never hardcodes a path or magic number.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
REPORTS_DIR = ROOT_DIR / "reports"

RAW_DATA_PATH = DATA_DIR / "insurance_claims.csv"

XGB_MODEL_PATH = MODELS_DIR / "xgboost_fraud_model.pkl"
ISOFOREST_MODEL_PATH = MODELS_DIR / "isolation_forest_model.pkl"
PREPROCESSOR_PATH = MODELS_DIR / "preprocessor.pkl"
LABEL_ENCODER_PATH = MODELS_DIR / "label_encoder.pkl"
FEATURE_METADATA_PATH = MODELS_DIR / "feature_metadata.json"
METRICS_PATH = REPORTS_DIR / "metrics.json"

for d in (MODELS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data / target configuration
# ---------------------------------------------------------------------------
TARGET_COLUMN = "fraud_reported"
ID_COLUMN = "policy_number"

# Columns dropped before modeling: identifiers, free-text/location fields,
# and the malformed trailing column present in the raw export.
DROP_COLUMNS = [
    "policy_number",
    "policy_bind_date",
    "incident_date",
    "incident_location",
    "insured_zip",
    "_c39",
]

RANDOM_STATE = 42
TEST_SIZE = 0.2

# ---------------------------------------------------------------------------
# Model hyperparameters
# ---------------------------------------------------------------------------
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "eval_metric": "logloss",
    "random_state": RANDOM_STATE,
    "scale_pos_weight": 3,   # add this line
}

ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,
    "contamination": 0.25,  # roughly matches observed fraud rate
    "random_state": RANDOM_STATE,
}

# Decision threshold applied to the XGBoost fraud probability when producing
# a binary fraud_label. Tunable independently of model training.
DECISION_THRESHOLD = 0.35

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://fraud_user:fraud_pass@localhost:5432/fraud_detection",
)

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------
API_TITLE = "Insurance Claims Fraud Detection API"
API_VERSION = "1.0.0"
