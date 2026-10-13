"""
PostgreSQL persistence layer using SQLAlchemy. Stores every scored claim
so predictions are auditable and queryable by downstream analysts.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src import config

engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PredictionORM(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, index=True)
    fraud_probability = Column(Float, nullable=False)
    fraud_label = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    request_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    """Create tables if they do not already exist. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_prediction(db: Session, claim_id: str, prediction: dict, payload: dict) -> PredictionORM:
    record = PredictionORM(
        claim_id=claim_id,
        fraud_probability=prediction["fraud_probability"],
        fraud_label=prediction["fraud_label"],
        risk_level=prediction["risk_level"],
        is_anomaly=prediction["is_anomaly"],
        request_payload=payload,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
