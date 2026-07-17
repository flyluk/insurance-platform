from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PolicyOut(BaseModel):
    id: str
    policy_number: str
    application_id: str
    party_id: str
    product_code: str
    status: str
    annual_premium: float
    risk_attributes: dict[str, Any]
    effective_date: datetime
    expiry_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EndorsementCreate(BaseModel):
    endorsement_type: str = "GENERAL"
    description: str | None = None
    premium_delta: float = 0.0
    risk_attributes: dict[str, Any] | None = None


class EndorsementOut(BaseModel):
    id: str
    policy_id: str
    endorsement_type: str
    description: str | None
    premium_delta: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
