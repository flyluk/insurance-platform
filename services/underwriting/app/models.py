import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class UnderwritingCase(Base):
    __tablename__ = "uw_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    application_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False)  # owner
    insured_party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    owner_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    insured_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    product_code: Mapped[str] = mapped_column(String(16), nullable=False)
    annual_premium: Mapped[float] = mapped_column(Float, nullable=False)
    risk_attributes: Mapped[dict] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), default=dict)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    # PENDING REFERRED ACCEPTED DECLINED
    auto_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
