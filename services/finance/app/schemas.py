from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from insurance_shared.parties import PartySummary


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
    owner: PartySummary | None = None

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    amount: float = Field(gt=0)
    method: Literal["CASH", "CARD", "ACH"] = "CASH"
    # Card (required when method=CARD) — simulated processor; never stored in full
    card_number: str | None = None
    card_exp_month: int | None = Field(default=None, ge=1, le=12)
    card_exp_year: int | None = Field(default=None, ge=2024, le=2100)
    card_cvv: str | None = None
    # ACH (required when method=ACH)
    account_name: str | None = None
    account_number: str | None = None
    routing_number: str | None = None


class PaymentOut(BaseModel):
    id: str
    invoice_id: str
    amount: float
    method: str
    reference: str | None = None
    masked_account: str | None = None
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
    owner: PartySummary | None = None

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
