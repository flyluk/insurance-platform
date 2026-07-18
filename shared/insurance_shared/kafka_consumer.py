"""Kafka consumer loop for domain events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Set
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.structs import OffsetAndMetadata

from insurance_shared.events import kafka_bootstrap, kafka_topic

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]

# Backoff before retrying a failed event so transient gaps (e.g. missing app row) can resolve.
_RETRY_SLEEP_SECONDS = 2.0


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
    await consumer.start()
    logger.info("Kafka consumer started group=%s topic=%s", group_id, kafka_topic())
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
                    if event_type not in handled_types:
                        await consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, "")})
                        continue
                    try:
                        await asyncio.to_thread(handler, event)
                        await consumer.commit({tp: OffsetAndMetadata(msg.offset + 1, "")})
                    except Exception:
                        logger.exception(
                            "Event handler failed group=%s event_id=%s type=%s; will retry",
                            group_id,
                            event.get("event_id"),
                            event_type,
                        )
                        await asyncio.sleep(_RETRY_SLEEP_SECONDS)
                        consumer.seek(tp, msg.offset)
    finally:
        await consumer.stop()
