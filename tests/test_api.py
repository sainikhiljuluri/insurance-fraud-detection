"""
Basic API tests. Requires models to be trained first (python -m src.train).
Uses SQLite fallback is NOT configured here — for /predict/store tests you
need a reachable PostgreSQL instance (see docker-compose.yml). The plain
/predict endpoint works without a database.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_CLAIM = {
    "months_as_customer": 328,
    "age": 48,
    "policy_state": "OH",
    "policy_csl": "250/500",
    "policy_deductable": 1000,
    "policy_annual_premium": 1406.91,
    "umbrella_limit": 0,
    "insured_sex": "MALE",
    "insured_education_level": "MD",
    "insured_occupation": "craft-repair",
    "insured_hobbies": "sleeping",
    "insured_relationship": "husband",
    "capital-gains": 53300,
    "capital-loss": 0,
    "incident_type": "Single Vehicle Collision",
    "collision_type": "Side Collision",
    "incident_severity": "Major Damage",
    "authorities_contacted": "Police",
    "incident_state": "SC",
    "incident_city": "Columbus",
    "incident_hour_of_the_day": 5,
    "number_of_vehicles_involved": 1,
    "property_damage": "YES",
    "bodily_injuries": 1,
    "witnesses": 2,
    "police_report_available": "YES",
    "total_claim_amount": 71610,
    "injury_claim": 6510,
    "property_claim": 13020,
    "vehicle_claim": 52080,
    "auto_make": "Saab",
    "auto_model": "92x",
    "auto_year": 2004,
    "claim_id": "CLAIM-TEST-001",
}


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_predict():
    resp = client.post("/predict", json=SAMPLE_CLAIM)
    assert resp.status_code == 200
    body = resp.json()
    assert body["claim_id"] == "CLAIM-TEST-001"
    assert 0.0 <= body["fraud_probability"] <= 1.0
    assert body["fraud_label"] in ("fraud", "not_fraud")
    assert body["risk_level"] in ("low", "medium", "high")
