from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from insurance_shared.parties import PartySummary

ProductCode = Literal["AUTO", "HOME", "LIFE"]


class PartyCreate(BaseModel):
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    date_of_birth: str = Field(min_length=1)
    address: str = Field(min_length=1)
    id_number: str = Field(min_length=1)
    gender: str = Field(min_length=1)


class PartyOut(BaseModel):
    id: str
    full_name: str
    email: str = ""
    phone: str | None = None
    date_of_birth: str | None = None
    address: str | None = None
    id_number: str | None = None
    gender: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class QuoteCreate(BaseModel):
    party_id: str  # policy owner / payer
    insured_party_id: str | None = None  # defaults to owner when omitted
    product_code: ProductCode
    plan_id: str
    rider_ids: list[str] = Field(default_factory=list)
    risk_attributes: dict[str, Any] = Field(default_factory=dict)


class QuoteOut(BaseModel):
    id: str
    party_id: str
    insured_party_id: str | None = None
    product_code: str
    plan_id: str | None = None
    rider_ids: list[str] = Field(default_factory=list)
    status: str
    risk_attributes: dict[str, Any]
    annual_premium: float | None
    currency: str
    created_at: datetime
    updated_at: datetime
    owner: PartySummary | None = None
    insured: PartySummary | None = None

    model_config = {"from_attributes": True}

    @field_validator("rider_ids", mode="before")
    @classmethod
    def _rider_ids(cls, value: Any) -> list:
        return value or []


class ApplicationOut(BaseModel):
    id: str
    application_number: str
    quote_id: str
    party_id: str
    insured_party_id: str | None = None
    product_code: str
    status: str
    risk_attributes: dict[str, Any]
    annual_premium: float
    uw_decision: str | None
    uw_reason: str | None
    policy_id: str | None
    policy_number: str | None = None
    created_at: datetime
    updated_at: datetime
    owner: PartySummary | None = None
    insured: PartySummary | None = None

    model_config = {"from_attributes": True}


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
