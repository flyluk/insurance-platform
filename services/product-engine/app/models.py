import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_premium: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_schema: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=lambda: []
    )
    uw_rules: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=lambda: {"decline": [], "refer": []}
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("product_code", "code", name="uq_plan_line_code"),)

    plan_riders: Mapped[list["PlanRider"]] = relationship(
        "PlanRider", back_populates="plan", cascade="all, delete-orphan"
    )
    rate_versions: Mapped[list["RateVersion"]] = relationship(
        "RateVersion",
        back_populates="plan",
        cascade="all, delete-orphan",
        foreign_keys="RateVersion.plan_id",
    )


class Rider(Base):
    __tablename__ = "riders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_code: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    premium: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("product_code", "code", name="uq_rider_line_code"),)

    plan_riders: Mapped[list["PlanRider"]] = relationship(
        "PlanRider", back_populates="rider", cascade="all, delete-orphan"
    )
    rate_versions: Mapped[list["RateVersion"]] = relationship(
        "RateVersion",
        back_populates="rider",
        cascade="all, delete-orphan",
        foreign_keys="RateVersion.rider_id",
    )


class PlanRider(Base):
    __tablename__ = "plan_riders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    rider_id: Mapped[str] = mapped_column(String(36), ForeignKey("riders.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("plan_id", "rider_id", name="uq_plan_rider"),)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="plan_riders")
    rider: Mapped["Rider"] = relationship("Rider", back_populates="plan_riders")


class RateVersion(Base):
    """Effective-dated premium for a plan or rider."""

    __tablename__ = "rate_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("riders.id", ondelete="CASCADE"), nullable=True, index=True
    )
    version_code: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plan: Mapped["Plan | None"] = relationship(
        "Plan", back_populates="rate_versions", foreign_keys=[plan_id]
    )
    rider: Mapped["Rider | None"] = relationship(
        "Rider", back_populates="rate_versions", foreign_keys=[rider_id]
    )
