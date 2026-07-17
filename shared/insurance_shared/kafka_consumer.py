"""Kafka consumer loop for domain events."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Set
from typing import Any

from aiokafka import AIOKafkaConsumer

from insurance_shared.events import kafka_bootstrap, kafka_topic

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], None]


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
        async for msg in consumer:
            event = msg.value
            event_type = event.get("event_type")
            if event_type not in handled_types:
                await consumer.commit()
                continue
            try:
                await asyncio.to_thread(handler, event)
                await consumer.commit()
            except Exception:
                logger.exception(
                    "Event handler failed group=%s event_id=%s type=%s",
                    group_id,
                    event.get("event_id"),
                    event_type,
                )
    finally:
        await consumer.stop()
