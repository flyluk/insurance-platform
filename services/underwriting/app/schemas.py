from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from insurance_shared.parties import PartySummary

Decision = Literal["ACCEPT", "REFER", "DECLINE"]


class CaseOut(BaseModel):
    id: str
    application_id: str
    application_number: str | None = None
    party_id: str
    insured_party_id: str | None = None
    product_code: str
    annual_premium: float
    risk_attributes: dict[str, Any]
    status: str
    auto_decision: str | None
    final_decision: str | None
    reason: str | None
    created_at: datetime
    updated_at: datetime
    owner: PartySummary | None = None
    insured: PartySummary | None = None

    model_config = {"from_attributes": True}


class DecisionIn(BaseModel):
    decision: Decision
    reason: str | None = None


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
