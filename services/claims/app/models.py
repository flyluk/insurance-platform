import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)  # policy owner
    insured_party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    owner_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    insured_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    product_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    # OPEN INVESTIGATING RESERVED SETTLED DENIED
    description: Mapped[str] = mapped_column(Text, nullable=False)
    loss_date: Mapped[str] = mapped_column(String(32), nullable=False)
    reserve_amount: Mapped[float] = mapped_column(Float, default=0.0)
    settlement_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ClaimDocument(Base):
    __tablename__ = "claim_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="OTHER")
    # PHOTO POLICE_REPORT MEDICAL INVOICE OTHER
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_by_role: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
