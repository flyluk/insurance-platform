from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from insurance_shared.parties import PartySummary


class PolicyOut(BaseModel):
    id: str
    policy_number: str
    application_id: str
    application_number: str | None = None
    party_id: str
    owner_party_id: str | None = None
    insured_party_id: str | None = None
    product_code: str
    status: str
    annual_premium: float
    risk_attributes: dict[str, Any]
    effective_date: datetime
    expiry_date: datetime
    cancelled_at: datetime | None = None
    cancellation_refund: float | None = None
    created_at: datetime
    updated_at: datetime
    owner: PartySummary | None = None
    insured: PartySummary | None = None

    model_config = {"from_attributes": True}


class EndorsementCreate(BaseModel):
    endorsement_type: str = "GENERAL"
    description: str | None = None
    # When True (default), recompute annual premium from risk + published rates.
    re_rate: bool = True
    # Used only when re_rate is False (manual override).
    premium_delta: float = 0.0
    risk_attributes: dict[str, Any] | None = None


class EndorsementOut(BaseModel):
    id: str
    policy_id: str
    endorsement_type: str
    description: str | None
    premium_delta: float
    billed_amount: float = 0.0
    created_at: datetime

    model_config = {"from_attributes": True}


class CancelPreviewOut(BaseModel):
    policy_id: str
    annual_premium: float
    term_days: int
    remaining_days: int
    remaining_fraction: float
    unearned_premium: float


class EndorsePreviewIn(BaseModel):
    risk_attributes: dict[str, Any] | None = None
    re_rate: bool = True
    premium_delta: float = 0.0


class EndorsePreviewOut(BaseModel):
    policy_id: str
    current_annual: float
    new_annual: float
    annual_delta: float
    remaining_fraction: float
    billed_amount: float


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
