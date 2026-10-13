"""
Pydantic request/response models for the fraud detection API.
ClaimRequest mirrors the raw insurance_claims.csv schema (minus the target
and identifier columns) so a caller can submit a new claim exactly as it
would appear in the source system.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ClaimRequest(BaseModel):
    months_as_customer: int = Field(..., example=328)
    age: int = Field(..., example=48)
    policy_state: str = Field(..., example="OH")
    policy_csl: str = Field(..., example="250/500")
    policy_deductable: int = Field(..., example=1000)
    policy_annual_premium: float = Field(..., example=1406.91)
    umbrella_limit: int = Field(..., example=0)
    insured_sex: str = Field(..., example="MALE")
    insured_education_level: str = Field(..., example="MD")
    insured_occupation: str = Field(..., example="craft-repair")
    insured_hobbies: str = Field(..., example="sleeping")
    insured_relationship: str = Field(..., example="husband")
    capital_gains: int = Field(..., alias="capital-gains", example=53300)
    capital_loss: int = Field(..., alias="capital-loss", example=0)
    incident_type: str = Field(..., example="Single Vehicle Collision")
    collision_type: Optional[str] = Field(None, example="Side Collision")
    incident_severity: str = Field(..., example="Major Damage")
    authorities_contacted: Optional[str] = Field(None, example="Police")
    incident_state: str = Field(..., example="SC")
    incident_city: str = Field(..., example="Columbus")
    incident_hour_of_the_day: int = Field(..., example=5)
    number_of_vehicles_involved: int = Field(..., example=1)
    property_damage: Optional[str] = Field(None, example="YES")
    bodily_injuries: int = Field(..., example=1)
    witnesses: int = Field(..., example=2)
    police_report_available: Optional[str] = Field(None, example="YES")
    total_claim_amount: float = Field(..., example=71610)
    injury_claim: float = Field(..., example=6510)
    property_claim: float = Field(..., example=13020)
    vehicle_claim: float = Field(..., example=52080)
    auto_make: str = Field(..., example="Saab")
    auto_model: str = Field(..., example="92x")
    auto_year: int = Field(..., example=2004)

    # Optional caller-supplied identifier for correlating stored predictions;
    # not used as a model feature.
    claim_id: Optional[str] = Field(None, example="CLAIM-1001")

    class Config:
        populate_by_name = True


class PredictionResponse(BaseModel):
    claim_id: str
    fraud_probability: float
    fraud_label: str
    risk_level: str
    is_anomaly: bool


class PredictionRecord(PredictionResponse):
    id: int
    created_at: str

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
