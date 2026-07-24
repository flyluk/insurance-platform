import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    application_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    application_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # owner (billing/auth)
    owner_party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    insured_party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    owner_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    insured_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    product_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE CANCELLED EXPIRED
    annual_premium: Mapped[float] = mapped_column(Float, nullable=False)
    risk_attributes: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expiry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_refund: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Endorsement(Base):
    __tablename__ = "endorsements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    endorsement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    premium_delta: Mapped[float] = mapped_column(Float, default=0.0)  # change to annual premium
    billed_amount: Mapped[float] = mapped_column(Float, default=0.0)  # mid-term prorated bill/credit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
