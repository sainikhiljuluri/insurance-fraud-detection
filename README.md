# Insurance Claims Fraud Detection System

An end-to-end machine learning solution for scoring insurance claims by
fraud risk, combining a supervised XGBoost classifier with an unsupervised
Isolation Forest anomaly detector, served through a FastAPI REST API and
backed by PostgreSQL. This matches the architecture described in the
accompanying project report.

## Project Structure

```
.
├── data/
│   └── insurance_claims.csv        # source dataset (1000 claims, 40 columns)
├── src/
│   ├── config.py                   # paths, hyperparameters, DB/API settings
│   ├── preprocessing.py            # cleaning, encoding, scaling pipeline
│   ├── train.py                    # trains XGBoost + Isolation Forest
│   ├── evaluate.py                 # metrics: accuracy/precision/recall/F1/ROC-AUC
│   └── predict.py                  # inference service used by the API
├── app/
│   ├── main.py                     # FastAPI application & routes
│   ├── schemas.py                  # Pydantic request/response models
│   └── database.py                 # SQLAlchemy models + PostgreSQL session
├── models/                         # serialized model artifacts (generated)
├── reports/                        # metrics.json (generated)
├── tests/
│   └── test_api.py                 # API tests
├── Dockerfile
├── docker-compose.yml              # API + PostgreSQL
├── requirements.txt
└── .env.example
```

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 1. Train the models

```bash
python -m src.train
```

This loads `data/insurance_claims.csv`, cleans it (drops identifiers,
converts `"?"` to NaN, encodes categoricals, scales numerics), trains both
models, evaluates the XGBoost classifier on a held-out 20% split, and
writes the following to `models/` and `reports/`:

- `xgboost_fraud_model.pkl`
- `isolation_forest_model.pkl`
- `preprocessor.pkl`
- `feature_metadata.json`
- `reports/metrics.json`

Sample output on the included dataset:

| Metric | Value |
|---|---|
| Accuracy | ~0.77 |
| Precision | ~0.54 |
| Recall | ~0.43 |
| F1-score | ~0.48 |
| ROC-AUC | ~0.82 |
| False Positive Rate | ~0.12 |

(Numbers vary slightly by environment/library version. The 1000-row
public dataset is much smaller than the ~1.2M-claim production assumption
in the report, so treat these as a functional baseline, not a final
production benchmark — see "Improving performance" below.)

## 2. Run the API

### Locally (no Docker)

```bash
export DATABASE_URL=postgresql+psycopg2://fraud_user:fraud_pass@localhost:5432/fraud_detection
uvicorn app.main:app --reload --port 8000
```

`/predict` works even without a reachable database; only `/predict/store`
and the `/predictions*` endpoints require PostgreSQL.

### With Docker (API + PostgreSQL)

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`, with interactive
docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check, confirms models are loaded |
| POST | `/predict` | Score a claim (no DB write) |
| POST | `/predict/store` | Score a claim and persist to PostgreSQL |
| GET | `/predictions/{claim_id}` | Retrieve stored predictions for a claim |
| GET | `/predictions?limit=20` | List recent stored predictions |

### Sample request

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
        "months_as_customer": 328, "age": 48, "policy_state": "OH",
        "policy_csl": "250/500", "policy_deductable": 1000,
        "policy_annual_premium": 1406.91, "umbrella_limit": 0,
        "insured_sex": "MALE", "insured_education_level": "MD",
        "insured_occupation": "craft-repair", "insured_hobbies": "sleeping",
        "insured_relationship": "husband", "capital-gains": 53300,
        "capital-loss": 0, "incident_type": "Single Vehicle Collision",
        "collision_type": "Side Collision", "incident_severity": "Major Damage",
        "authorities_contacted": "Police", "incident_state": "SC",
        "incident_city": "Columbus", "incident_hour_of_the_day": 5,
        "number_of_vehicles_involved": 1, "property_damage": "YES",
        "bodily_injuries": 1, "witnesses": 2, "police_report_available": "YES",
        "total_claim_amount": 71610, "injury_claim": 6510,
        "property_claim": 13020, "vehicle_claim": 52080,
        "auto_make": "Saab", "auto_model": "92x", "auto_year": 2004,
        "claim_id": "CLAIM-1001"
      }'
```

### Sample response

```json
{
  "claim_id": "CLAIM-1001",
  "fraud_probability": 0.93,
  "fraud_label": "fraud",
  "risk_level": "high",
  "is_anomaly": true
}
```

## 3. Run tests

```bash
pytest tests/ -v
```

`/predict`-based tests run without any external dependency. Tests that
exercise `/predict/store` need PostgreSQL reachable (start it with
`docker compose up db`).

## Improving performance

The bundled 1000-row dataset is a well-known public sample and is small
relative to the production scale (~1.2M claims) assumed in the report. To
move toward the target performance figures (93% fraud detection rate, 7%
false-positive rate) in a real deployment:

- Train on the full historical volume rather than the 1000-row sample.
- Tune `XGB_PARAMS` / the decision `DECISION_THRESHOLD` in `src/config.py`
  against a validation set (see `evaluate_at_multiple_thresholds` in
  `src/evaluate.py`).
- Address class imbalance explicitly (e.g. `scale_pos_weight` in XGBoost).
- Add periodic retraining as fraud patterns drift over time.

## Tech Stack

Python, Pandas, NumPy, scikit-learn, XGBoost, Isolation Forest, FastAPI,
PostgreSQL (SQLAlchemy), Docker, Docker Compose.
