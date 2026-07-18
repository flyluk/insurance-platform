"""Kafka consumer loop for domain events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from collections.abc import Callable, Set
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import OffsetAndMetadata

from insurance_shared.events import kafka_bootstrap, kafka_topic

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]

# Backoff before retrying a failed event so transient gaps (e.g. missing app row) can resolve.
_RETRY_SLEEP_SECONDS = float(os.getenv("KAFKA_HANDLER_RETRY_SLEEP_SECONDS", "2.0"))
# Cap retries so poison / permanent failures cannot block a partition forever.
_MAX_RETRIES = int(os.getenv("KAFKA_HANDLER_MAX_RETRIES", "15"))
# Errors that will not recover by waiting (malformed payload, missing keys, bad types).
_PERMANENT_ERRORS = (KeyError, TypeError, ValueError, AttributeError, json.JSONDecodeError)


def kafka_dlq_topic() -> str:
    return os.getenv("KAFKA_DOMAIN_EVENTS_DLQ_TOPIC", f"{kafka_topic()}.dlq")


def _is_permanent(exc: BaseException) -> bool:
    return isinstance(exc, _PERMANENT_ERRORS)


def _max_attempts_for(exc: BaseException) -> int:
    # Permanent errors: one attempt then DLQ. Transient (e.g. LookupError): full budget.
    if _is_permanent(exc):
        return 1
    return max(1, _MAX_RETRIES)


async def _publish_dlq(
    producer: AIOKafkaProducer,
    *,
    group_id: str,
    event: dict[str, Any],
    topic: str,
    partition: int,
    offset: int,
    attempts: int,
    error: BaseException,
) -> None:
    envelope = {
        "original_topic": topic,
        "original_partition": partition,
        "original_offset": offset,
        "consumer_group": group_id,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "attempts": attempts,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
        "event": event,
    }
    key = (event.get("event_type") or "unknown").encode()
    await producer.send_and_wait(kafka_dlq_topic(), envelope, key=key)


async def kafka_event_consumer(
    *,
    group_id: str,
    handled_types: Set[str],
    handler: EventHandler,
) -> None:
    consumer = AIOKafkaConsumer(
        kafka_topic(),
        bootstrap_servers=kafka_bootstrap(),
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap(),
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )
    await consumer.start()
    await producer.start()
    logger.info(
        "Kafka consumer started group=%s topic=%s dlq=%s max_retries=%s",
        group_id,
        kafka_topic(),
        kafka_dlq_topic(),
        _MAX_RETRIES,
    )
    # Attempts keyed by (partition, offset) so seek/retry does not reset the budget incorrectly
    # when the same message is re-fetched.
    attempts: dict[tuple[int, int], int] = {}
    try:
        # Use getmany (not async-for) so a failed handler can seek back to the same
        # offset. Committing a later message must never skip an unprocessed one.
        while True:
            batches = await consumer.getmany(timeout_ms=1000, max_records=1)
            if not batches:
                await asyncio.sleep(0.05)
                continue
            for tp, messages in batches.items():
                for msg in messages:
                    event = msg.value
                    event_type = event.get("event_type")
                    attempt_key = (msg.partition, msg.offset)
                    if event_type not in handled_types:
                        await consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, "")})
                        attempts.pop(attempt_key, None)
                        continue
                    try:
                        await asyncio.to_thread(handler, event)
                        await consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, "")})
                        attempts.pop(attempt_key, None)
                    except Exception as exc:
                        n = attempts.get(attempt_key, 0) + 1
                        attempts[attempt_key] = n
                        max_attempts = _max_attempts_for(exc)
                        if n < max_attempts:
                            logger.exception(
                                "Event handler failed group=%s event_id=%s type=%s "
                                "attempt=%s/%s; will retry",
                                group_id,
                                event.get("event_id"),
                                event_type,
                                n,
                                max_attempts,
                            )
                            await asyncio.sleep(_RETRY_SLEEP_SECONDS)
                            consumer.seek(tp, msg.offset)
                            continue

                        logger.exception(
                            "Event handler exhausted retries group=%s event_id=%s type=%s "
                            "attempts=%s; sending to DLQ %s",
                            group_id,
                            event.get("event_id"),
                            event_type,
                            n,
                            kafka_dlq_topic(),
                        )
                        try:
                            await _publish_dlq(
                                producer,
                                group_id=group_id,
                                event=event if isinstance(event, dict) else {"raw": event},
                                topic=msg.topic,
                                partition=msg.partition,
                                offset=msg.offset,
                                attempts=n,
                                error=exc,
                            )
                        except Exception:
                            logger.exception(
                                "DLQ publish failed group=%s event_id=%s; committing anyway "
                                "to unblock partition",
                                group_id,
                                event.get("event_id") if isinstance(event, dict) else None,
                            )
                        await consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, "")})
                        attempts.pop(attempt_key, None)
    finally:
        await consumer.stop()
        await producer.stop()
