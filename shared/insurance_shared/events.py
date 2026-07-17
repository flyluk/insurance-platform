"""Postgres outbox + Kafka domain event bus."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

logger = logging.getLogger(__name__)

DEFAULT_TOPIC = "insurance.domain.events"


class OutboxBase(DeclarativeBase):
    pass


class OutboxEvent(OutboxBase):
    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    destination_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
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


def kafka_bootstrap() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


def kafka_topic() -> str:
    return os.getenv("KAFKA_DOMAIN_EVENTS_TOPIC", DEFAULT_TOPIC)


def event_envelope(
    *,
    event_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
        "payload": payload,
    }


def enqueue_event(
    db: Session,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    event_id: str | None = None,
    destination_url: str = "",
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
    """Publish unpublished outbox rows to Kafka."""
    from aiokafka import AIOKafkaProducer

    published = 0
    db: Session = db_factory()
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap(),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
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
        for row in rows:
            body = event_envelope(
                event_id=row.id,
                event_type=row.event_type,
                aggregate_type=row.aggregate_type,
                aggregate_id=row.aggregate_id,
                payload=json.loads(row.payload),
            )
            try:
                await producer.send_and_wait(kafka_topic(), body, key=row.event_type.encode())
                row.published = True
                row.published_at = datetime.now(timezone.utc)
                published += 1
            except Exception:
                logger.exception("Kafka publish failed for outbox %s", row.id)
        db.commit()
    finally:
        await producer.stop()
        db.close()
    return published


async def outbox_poller(db_factory, interval_seconds: float = 2.0) -> None:
    while True:
        try:
            await publish_pending(db_factory)
        except Exception:
            logger.exception("Outbox poller cycle failed")
        await asyncio.sleep(interval_seconds)
