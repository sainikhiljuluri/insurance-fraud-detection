# Insurance Fraud Detection — Study Guide

A complete walkthrough of how this project works, file by file, concept by concept — written so you can explain every part of it, not just run it.

---

## 1. The big picture

```
raw CSV → clean → encode/scale → train 2 models → save artifacts → FastAPI loads them → serves predictions → Postgres stores results
```

Two models work together on every claim:

| Model | Type | What it answers |
|---|---|---|
| **XGBoost classifier** | Supervised | "Based on claims we've seen labeled fraud/not-fraud before, how likely is *this* claim to be fraud?" → a probability |
| **Isolation Forest** | Unsupervised (anomaly detection) | "Does this claim look statistically unusual compared to normal claims, regardless of any label?" → a flag |

Why both? XGBoost is only as good as its labeled training examples — it can miss genuinely new fraud patterns it's never seen. Isolation Forest doesn't need labels at all; it just looks for claims that sit far from the "normal" cluster. Together they cover two different failure modes: known fraud patterns (XGBoost) and novel/weird ones (Isolation Forest).

---

## 2. Project structure

```
├── data/insurance_claims.csv       # raw training data (1,000 rows)
├── src/
│   ├── config.py                   # every path, hyperparameter, constant — single source of truth
│   ├── preprocessing.py            # cleaning + encoding + scaling pipeline
│   ├── train.py                    # trains both models, saves artifacts
│   ├── evaluate.py                 # computes accuracy/precision/recall/etc.
│   └── predict.py                  # loads saved models, scores one claim
├── app/
│   ├── main.py                     # FastAPI endpoints
│   ├── database.py                 # SQLAlchemy models + Postgres connection
│   └── schemas.py                  # Pydantic request/response validation
├── models/                         # saved .pkl files (created by train.py)
├── reports/metrics.json            # saved evaluation numbers (created by train.py)
└── tests/test_api.py               # automated tests
```

**Design principle worth noticing:** `config.py` is the *only* place hyperparameters, paths, and constants are defined. Every other file imports from it (`from src import config`). This means changing `DECISION_THRESHOLD` or `XGB_PARAMS` in one place changes it everywhere — no hunting through files for a hardcoded `0.5`. This is a real production-code habit, not a toy-project shortcut.

---

## 3. `config.py` — the control panel

```python
XGB_PARAMS = {
    "n_estimators": 300,        # how many decision trees to build, sequentially
    "max_depth": 4,             # how deep each tree can grow (shallow = less overfitting)
    "learning_rate": 0.05,      # how much each new tree corrects the previous ones' errors
    "subsample": 0.8,           # each tree sees only 80% of rows (reduces overfitting)
    "colsample_bytree": 0.8,    # each tree sees only 80% of columns (same reason)
    "min_child_weight": 3,      # minimum data needed in a leaf before splitting further
}

ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,        # how many random trees vote on "is this normal or weird"
    "contamination": 0.25,      # our prior belief: ~25% of claims are fraud (matches the real rate)
}

DECISION_THRESHOLD = 0.5        # probability ≥ this → labeled "fraud"
```

**Key concept — the decision threshold.** XGBoost doesn't output "fraud" or "not fraud" — it outputs a probability between 0 and 1. Something has to decide where the cutoff is. `0.5` is the naive default (majority vote), but it's rarely optimal for imbalanced problems like fraud, where missing a fraud case (false negative) is usually costlier than a false alarm (false positive). This is exactly why `evaluate_at_multiple_thresholds()` exists in `evaluate.py` — to let you find a better cutoff than the default.

---

## 4. `preprocessing.py` — turning raw claims into numbers

Models can't read text like `"policy_state": "OH"` — everything has to become numbers. This file's job is that translation, done consistently for both training and later predictions.

**Step by step:**

1. **`clean_data()`** — drops identifier columns (`policy_number`, dates, free-text location) that would let the model "cheat" by memorizing specific claims instead of learning patterns, and converts the literal string `"?"` (used in the raw CSV for missing values) into a proper `NaN`.

2. **`split_features_target()`** — separates the label (`fraud_reported`, mapped from `"Y"/"N"` to `1/0`) from everything else.

3. **`infer_feature_types()`** — automatically sorts columns into numeric (16 columns: age, claim amounts, etc.) vs categorical (17 columns: state, occupation, incident type, etc.) based on dtype.

4. **`build_preprocessor()`** — builds an sklearn `ColumnTransformer` with two parallel pipelines:
   - **Numeric pipeline:** fill missing values with the *median* → `StandardScaler` (rescales every number to mean 0, std 1, so no single feature like `total_claim_amount` in the tens of thousands dominates a feature like `witnesses` which only ranges 0–3)
   - **Categorical pipeline:** fill missing values with the *most frequent* value → `OneHotEncoder` (turns `policy_state: OH` into a set of binary columns like `policy_state_OH=1, policy_state_CA=0, policy_state_NY=0...`)

   This is why training logs show **157 output features** from just 33 input columns — one-hot encoding a 17-category column like `insured_hobbies` alone creates dozens of binary columns.

5. **The preprocessor gets saved** (`preprocessor.pkl`) after training and reused unchanged at prediction time — critical, because if you re-fit a new `StandardScaler` on a single incoming claim, the scaling would be meaningless (you need the *training set's* mean/std, not a single row's).

**Concept: why fit only on training data.** `preprocessor.fit_transform(X)` in `train.py` runs on the full dataset before the train/test split conceptually — but note the actual code fits before splitting. This is worth knowing as a subtlety: a stricter pipeline would fit the preprocessor on `X_train` only, then `.transform()` (not `.fit_transform()`) on `X_test`, to avoid any information about the test set's distribution leaking into scaling/encoding. This project currently fits before splitting — a good thing to flag if you want to demonstrate you understand data leakage.

---

## 5. `train.py` — the training script

Run with `python -m src.train`. Sequence:

1. **Load + preprocess** the full dataset via `prepare_training_data()`.
2. **Split** into 800 train / 200 test rows (`test_size=0.2`), using `stratify=y` — this guarantees both splits have the same ~24.7% fraud rate, rather than risking an unlucky split where the test set has almost no fraud examples at all (which would make evaluation meaningless).
3. **Train XGBoost** — a *gradient boosting* classifier. Unlike a single decision tree, it builds trees one at a time, where each new tree is trained specifically to correct the mistakes of all trees before it. `n_estimators=300` means 300 such trees, each nudging the prediction slightly.
4. **Train Isolation Forest** — builds random trees that repeatedly split data on random features/thresholds. The intuition: an outlier gets isolated into its own tiny partition in *very few* splits (it's "easy to isolate" because it's far from everything else), while a normal point takes many splits to separate from its neighbors. Average "splits needed" across all trees → anomaly score.
5. **Evaluate** on the held-out 200-row test set (see section 6).
6. **Cross-check the two models** — `isolation_forest_agreement_with_labels` measures how often the *unsupervised* Isolation Forest's anomaly flag happens to match the *supervised* fraud label. This isn't a formal metric (Isolation Forest isn't meant to predict labels), but it's a useful sanity signal — 0.625 tells you the anomaly signal captures a real but partial fraud signature.
7. **Save everything** — both models, the preprocessor, and `feature_metadata.json` (which records exactly what columns/order the model expects, so `predict.py` can validate a new claim matches).

---

## 6. `evaluate.py` — how "good" is measured

```python
tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
```

This is the confusion matrix — the foundation everything else is built from:

|  | Predicted: not fraud | Predicted: fraud |
|---|---|---|
| **Actually not fraud** | True Negative (tn) | False Positive (fp) |
| **Actually fraud** | False Negative (fn) | True Positive (tp) |

From your real run: `tn=132, fp=19, fn=28, tp=21`.

| Metric | Formula | Real value | Plain-English meaning |
|---|---|---|---|
| **Accuracy** | (tp+tn) / total | 0.765 | % of all claims classified correctly — misleading alone on imbalanced data |
| **Precision** | tp / (tp+fp) | 0.525 | Of claims flagged as fraud, how many actually were fraud |
| **Recall** | tp / (tp+fn) | 0.429 | Of claims that were actually fraud, how many did we catch |
| **F1-score** | harmonic mean of precision & recall | 0.472 | Single number balancing both |
| **ROC-AUC** | area under ROC curve | 0.815 | How well the model ranks fraud above non-fraud *across all thresholds*, independent of the 0.5 cutoff |
| **False Positive Rate** | fp / (fp+tn) | 0.126 | Of legitimate claims, how many get wrongly flagged |

**Why recall (0.43) matters most here.** In fraud detection, missing real fraud (a false negative) usually costs more than a false alarm (a false positive gets manually reviewed and dismissed). A recall of 43% means **more than half of actual fraud cases slip through** at the current 0.5 threshold — this is the single most important number to improve, and it's exactly what threshold tuning and `scale_pos_weight` target.

**`evaluate_at_multiple_thresholds()`** exists for exactly this: it re-runs the confusion matrix at every threshold from 0.1 to 0.9, letting you see the precision/recall tradeoff and pick a threshold that favors recall (e.g. 0.3 instead of 0.5) — at the cost of more false positives.

---

## 7. `predict.py` — turning a saved model into a live prediction

`FraudModelService` is a small wrapper class that:
- Loads all three artifacts (preprocessor, XGBoost model, Isolation Forest) **once**, cached via `@lru_cache(maxsize=1)` — so the API doesn't reload multi-MB model files from disk on every single request, only on the very first one.
- `.predict(claim_dict)` runs one claim through the exact same cleaning/transform pipeline used in training, then:
  - Gets `fraud_probability` from XGBoost
  - Converts it to `fraud_label` using `DECISION_THRESHOLD`
  - Buckets it into a human-readable `risk_level` (`low` < 0.4 ≤ `medium` < 0.75 ≤ `high`) — a business-friendly layer on top of the raw probability
  - Runs the same claim through Isolation Forest for the `is_anomaly` flag

This is the *inference* half of the ML lifecycle, mirroring the *training* half — same preprocessing code (`clean_data`, `split_features_target` reused), so predictions can never drift from how the model was actually trained.

---

## 8. `app/` — the FastAPI service

**`schemas.py`** — defines what a valid request/response looks like using Pydantic. Two things worth noting:
- `Field(..., alias="capital-gains")` — Python variable names can't contain hyphens, but the source CSV column is `capital-gains`, so Pydantic's `alias` mechanism lets the Python code use `capital_gains` internally while still accepting/producing the hyphenated JSON key the schema requires.
- FastAPI auto-generates the entire Swagger UI (`/docs`) directly from these Pydantic models — that's *why* `/docs` exists with zero extra code.

**`database.py`** — SQLAlchemy ORM layer:
- `PredictionORM` is a Python class that maps directly to a Postgres table (`predictions`) — each class attribute (`claim_id`, `fraud_probability`...) becomes a column.
- `request_payload = Column(JSON)` stores the *entire original claim* as JSON alongside the prediction — meaning you can always trace back exactly what inputs produced any stored result, which matters a lot for an auditable fraud system.
- `get_db()` is a *generator* used as a FastAPI dependency (`Depends(get_db)`) — it opens a database session, hands it to the endpoint function, and guarantees the session is closed afterward (the `finally: db.close()`) even if the endpoint raises an error.

**`main.py`** — five endpoints:

| Endpoint | Method | What it does |
|---|---|---|
| `/health` | GET | Confirms the API is up and models loaded successfully |
| `/predict` | POST | Scores a claim, returns the result, doesn't touch the database |
| `/predict/store` | POST | Scores a claim *and* saves it to Postgres |
| `/predictions/{claim_id}` | GET | Retrieves all stored predictions for one specific claim |
| `/predictions` | GET | Lists the most recent predictions across all claims |

**Key pattern — `lifespan`:** the `@asynccontextmanager` function runs `init_db()` once when the API starts up (creating the `predictions` table if it doesn't exist yet) and is wrapped in a `try/except` so that a database failure doesn't crash the whole API — it just logs a warning and lets `/predict` (which doesn't need the DB) keep working. This is exactly the behavior you saw earlier when the native Postgres conflict caused a warning but `/predict` still worked fine.

---

## 9. Testing (`tests/test_api.py`)

Uses `TestClient` from FastAPI, which lets tests call endpoints in-process (no real server/network needed) — fast and doesn't require uvicorn to be running. `test_health` and `test_predict` don't need a database; the store/list tests do, since they exercise the full DB round-trip.

---

## 10. Skills this project demonstrates

If you're studying this to know what to say you've learned:

**Machine learning**
- Supervised classification (gradient boosting / XGBoost)
- Unsupervised anomaly detection (Isolation Forest)
- Feature engineering: imputation, one-hot encoding, standardization
- Train/test splitting with stratification for imbalanced classes
- Evaluation beyond accuracy: precision, recall, F1, ROC-AUC, confusion matrix
- Threshold tuning as a separate lever from model training
- Understanding class imbalance and why raw accuracy misleads

**Software engineering**
- Centralized configuration (single source of truth, no magic numbers)
- Separation of concerns: preprocessing / training / evaluation / inference / API as distinct modules
- Reusable, serialized pipelines (fit once, replay identically at inference)
- Caching expensive resources (`@lru_cache` for model loading)
- Structured logging throughout

**API & backend**
- REST API design with FastAPI
- Request/response validation with Pydantic (including field aliasing)
- Auto-generated interactive documentation (Swagger UI)
- ORM-based database access with SQLAlchemy
- Dependency injection pattern (`Depends(get_db)`)
- Graceful degradation (API stays partially functional if the DB is down)

**Infrastructure**
- Containerization with Docker and Docker Compose
- Environment-based configuration (`.env` / `python-dotenv`)
- Multi-service orchestration (API + database as separate containers)
- Persistent storage via Docker volumes

---

## 11. Questions worth being able to answer out loud

- Why two models instead of one? *(complementary failure modes — known vs novel fraud patterns)*
- Why is 77% accuracy not actually good here? *(class imbalance — ~75% of claims aren't fraud, so a model that always predicts "not fraud" would already score ~75%)*
- What would you change to catch more fraud? *(lower the decision threshold, or set `scale_pos_weight` in XGBoost to penalize missing the minority class more heavily)*
- Why is the preprocessor saved and reused instead of refit at prediction time? *(consistency — a single new claim doesn't have a meaningful mean/std of its own to scale against)*
- What happens if the database is down? *(`/predict` still works; only `/predict/store` and the `/predictions` endpoints fail, thanks to the lifespan try/except)*
