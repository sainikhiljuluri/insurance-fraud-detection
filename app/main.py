"""
FastAPI service exposing the fraud detection models over REST.

Endpoints:
  GET  /health              - liveness / model-load check
  POST /predict              - score a single claim (models only, no DB write)
  POST /predict/store        - score a claim and persist the result to PostgreSQL
  GET  /predictions/{claim_id} - retrieve stored predictions for a claim
  GET  /predictions          - list recent stored predictions

Run locally:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src import config
from src.predict import get_model_service
from app.schemas import ClaimRequest, PredictionResponse, PredictionRecord, HealthResponse
from app.database import init_db, get_db, save_prediction, PredictionORM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as exc:  # pragma: no cover - startup diagnostics only
        logger.warning("Database initialization skipped/failed: %s", exc)
    yield


app = FastAPI(title=config.API_TITLE, version=config.API_VERSION, lifespan=lifespan)

#For UI 
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your actual frontend URL before deploying
    allow_methods=["*"],
    allow_headers=["*"],
)

def _claim_dict(claim: ClaimRequest) -> dict:
    """Convert the request model to the raw-column dict the pipeline expects."""
    data = claim.model_dump(by_alias=True, exclude={"claim_id"})
    return data


@app.get("/health", response_model=HealthResponse)
def health():
    models_loaded = True
    try:
        get_model_service()
    except Exception:
        models_loaded = False
    return HealthResponse(status="ok", models_loaded=models_loaded)


@app.post("/predict", response_model=PredictionResponse)
def predict(claim: ClaimRequest):
    """Score a claim without writing to the database."""
    service = get_model_service()
    claim_id = claim.claim_id or f"CLAIM-{uuid.uuid4().hex[:8].upper()}"
    try:
        result = service.predict(_claim_dict(claim))
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=400, detail=f"Prediction failed: {exc}") from exc
    return PredictionResponse(claim_id=claim_id, **result)


@app.post("/predict/store", response_model=PredictionRecord)
def predict_and_store(claim: ClaimRequest, db: Session = Depends(get_db)):
    """Score a claim and persist the prediction (and raw payload) to PostgreSQL."""
    service = get_model_service()
    claim_id = claim.claim_id or f"CLAIM-{uuid.uuid4().hex[:8].upper()}"
    try:
        result = service.predict(_claim_dict(claim))
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=400, detail=f"Prediction failed: {exc}") from exc

    record = save_prediction(db, claim_id=claim_id, prediction=result, payload=claim.model_dump(by_alias=True))
    return PredictionRecord(
        id=record.id,
        claim_id=record.claim_id,
        fraud_probability=record.fraud_probability,
        fraud_label=record.fraud_label,
        risk_level=record.risk_level,
        is_anomaly=record.is_anomaly,
        created_at=record.created_at.isoformat(),
    )


@app.get("/predictions/{claim_id}", response_model=list[PredictionRecord])
def get_predictions_for_claim(claim_id: str, db: Session = Depends(get_db)):
    records = (
        db.query(PredictionORM)
        .filter(PredictionORM.claim_id == claim_id)
        .order_by(desc(PredictionORM.created_at))
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail="No predictions found for this claim_id")
    return [
        PredictionRecord(
            id=r.id, claim_id=r.claim_id, fraud_probability=r.fraud_probability,
            fraud_label=r.fraud_label, risk_level=r.risk_level, is_anomaly=r.is_anomaly,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]


@app.get("/predictions", response_model=list[PredictionRecord])
def list_recent_predictions(limit: int = 20, db: Session = Depends(get_db)):
    records = db.query(PredictionORM).order_by(desc(PredictionORM.created_at)).limit(limit).all()
    return [
        PredictionRecord(
            id=r.id, claim_id=r.claim_id, fraud_probability=r.fraud_probability,
            fraud_label=r.fraud_label, risk_level=r.risk_level, is_anomaly=r.is_anomaly,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
