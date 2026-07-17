from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InvoiceOut(BaseModel):
    id: str
    invoice_number: str
    policy_id: str | None
    party_id: str
    invoice_type: str
    amount: float
    status: str
    description: str | None
    created_at: datetime
    paid_at: datetime | None

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: str = "CASH"


class PaymentOut(BaseModel):
    id: str
    invoice_id: str
    amount: float
    method: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DisbursementOut(BaseModel):
    id: str
    claim_id: str
    claim_number: str
    policy_id: str
    party_id: str
    amount: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JournalLineOut(BaseModel):
    id: str
    entry_id: str
    account: str
    debit: float
    credit: float

    model_config = {"from_attributes": True}


class JournalEntryOut(BaseModel):
    id: str
    reference_type: str
    reference_id: str
    memo: str
    created_at: datetime
    lines: list[JournalLineOut] = []

    model_config = {"from_attributes": True}


class DomainEventIn(BaseModel):
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]
