from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ProductCode = Literal["AUTO", "HOME", "LIFE"]


class PartyCreate(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    date_of_birth: str | None = None
    address: str | None = None


class PartyOut(PartyCreate):
    id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteCreate(BaseModel):
    party_id: str
    product_code: ProductCode
    risk_attributes: dict[str, Any] = Field(default_factory=dict)


class QuoteOut(BaseModel):
    id: str
    party_id: str
    product_code: str
    status: str
    risk_attributes: dict[str, Any]
    annual_premium: float | None
    currency: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: str
    quote_id: str
    party_id: str
    product_code: str
    status: str
    risk_attributes: dict[str, Any]
    annual_premium: float
    uw_decision: str | None
    uw_reason: str | None
    policy_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
