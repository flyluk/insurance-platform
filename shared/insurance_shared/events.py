"""Postgres outbox helpers and HTTP event delivery."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

logger = logging.getLogger(__name__)


class OutboxBase(DeclarativeBase):
    pass


class OutboxEvent(OutboxBase):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    destination_url: Mapped[str] = mapped_column(String(512), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessedEvent(OutboxBase):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def enqueue_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    destination_url: str,
    event_id: str | None = None,
) -> OutboxEvent:
    evt = OutboxEvent(
        id=event_id or str(uuid.uuid4()),
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=json.dumps(payload),
        destination_url=destination_url,
        published=False,
    )
    db.add(evt)
    return evt


def already_processed(db: Session, event_id: str) -> bool:
    return db.get(ProcessedEvent, event_id) is not None


def mark_processed(db: Session, event_id: str, event_type: str) -> None:
    db.add(ProcessedEvent(event_id=event_id, event_type=event_type))


async def publish_pending(db_factory, batch_size: int = 20) -> int:
    """Publish unpublished outbox rows. db_factory yields a Session."""
    published = 0
    db: Session = db_factory()
    try:
        rows = (
            db.execute(
                select(OutboxEvent)
                .where(OutboxEvent.published.is_(False))
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
            )
            .scalars()
            .all()
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            for row in rows:
                body = {
                    "event_id": row.id,
                    "event_type": row.event_type,
                    "aggregate_type": row.aggregate_type,
                    "aggregate_id": row.aggregate_id,
                    "payload": json.loads(row.payload),
                }
                try:
                    resp = await client.post(row.destination_url, json=body)
                    if resp.status_code < 300:
                        row.published = True
                        row.published_at = datetime.now(timezone.utc)
                        published += 1
                    else:
                        logger.warning(
                            "Outbox publish failed %s -> %s status=%s body=%s",
                            row.id,
                            row.destination_url,
                            resp.status_code,
                            resp.text[:200],
                        )
                except Exception:
                    logger.exception("Outbox publish error for %s", row.id)
        db.commit()
    finally:
        db.close()
    return published


async def outbox_poller(db_factory, interval_seconds: float = 2.0) -> None:
    while True:
        try:
            await publish_pending(db_factory)
        except Exception:
            logger.exception("Outbox poller cycle failed")
        await asyncio.sleep(interval_seconds)
