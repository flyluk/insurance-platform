from datetime import datetime

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    policy_id: str
    party_id: str
    product_code: str
    description: str
    loss_date: str
    reserve_amount: float = 0.0


class ReserveUpdate(BaseModel):
    reserve_amount: float = Field(gt=0)


class SettleIn(BaseModel):
    settlement_amount: float = Field(gt=0)


class ClaimOut(BaseModel):
    id: str
    claim_number: str
    policy_id: str
    party_id: str
    product_code: str
    status: str
    description: str
    loss_date: str
    reserve_amount: float
    settlement_amount: float | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict
