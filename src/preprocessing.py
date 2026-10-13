"""
Data preprocessing pipeline for the Insurance Claims Fraud Detection System.

Responsible for:
  - loading raw claim data
  - cleaning ('?' placeholders, malformed columns, dtype fixes)
  - encoding categorical variables
  - scaling numerical variables
  - producing a reusable sklearn ColumnTransformer that is serialized
    alongside the trained models so the exact same transformation can be
    replayed at inference time.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder

from src import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_raw_data(path: Path = config.RAW_DATA_PATH) -> pd.DataFrame:
    """Load the raw insurance claims CSV."""
    logger.info("Loading raw data from %s", path)
    df = pd.read_csv(path)
    logger.info("Loaded %d rows, %d columns", *df.shape)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply cleaning rules common to both training and inference data."""
    df = df.copy()

    # The source export contains a fully-empty trailing column (_c39) and
    # uses the literal string "?" for missing categorical values.
    df = df.drop(columns=[c for c in config.DROP_COLUMNS if c in df.columns], errors="ignore")
    df = df.replace("?", np.nan)

    # Normalize column names defensively (strip whitespace).
    df.columns = [c.strip() for c in df.columns]

    # Drop fully empty columns/rows that may remain.
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    return df


def split_features_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series | None]:
    """Split a cleaned dataframe into X (features) and y (target, if present)."""
    if config.TARGET_COLUMN in df.columns:
        y = df[config.TARGET_COLUMN].map({"Y": 1, "N": 0}).astype(int)
        X = df.drop(columns=[config.TARGET_COLUMN])
    else:
        y = None
        X = df.copy()
    return X, y


def infer_feature_types(X: pd.DataFrame) -> Tuple[list, list]:
    """Split feature columns into numeric and categorical groups."""
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = X.select_dtypes(exclude=[np.number]).columns.tolist()
    return numeric_cols, categorical_cols


def build_preprocessor(numeric_cols: list, categorical_cols: list) -> ColumnTransformer:
    """Build the sklearn ColumnTransformer used for both models."""
    numeric_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_cols),
            ("cat", categorical_pipeline, categorical_cols),
        ],
        remainder="drop",
    )
    return preprocessor


def get_feature_names(preprocessor: ColumnTransformer) -> list:
    """Return the flat list of output feature names after transformation."""
    return list(preprocessor.get_feature_names_out())


def prepare_training_data(path: Path = config.RAW_DATA_PATH):
    """
    End-to-end preparation used by the training script:
      raw CSV -> cleaned -> split -> fitted preprocessor -> transformed arrays
    """
    df = load_raw_data(path)
    df = clean_data(df)
    X, y = split_features_target(df)

    numeric_cols, categorical_cols = infer_feature_types(X)
    logger.info("Numeric features (%d): %s", len(numeric_cols), numeric_cols)
    logger.info("Categorical features (%d): %s", len(categorical_cols), categorical_cols)

    preprocessor = build_preprocessor(numeric_cols, categorical_cols)
    X_transformed = preprocessor.fit_transform(X)
    feature_names = get_feature_names(preprocessor)

    return X_transformed, y, preprocessor, feature_names, numeric_cols, categorical_cols


def prepare_inference_data(df: pd.DataFrame, preprocessor: ColumnTransformer) -> np.ndarray:
    """Transform new/unseen claim records using an already-fitted preprocessor."""
    df = clean_data(df)
    X, _ = split_features_target(df)
    return preprocessor.transform(X)
