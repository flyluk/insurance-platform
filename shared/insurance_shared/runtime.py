import asyncio
from collections.abc import Callable, Set
from contextlib import asynccontextmanager
from typing import Any

from insurance_shared.events import outbox_poller
from insurance_shared.kafka_consumer import kafka_event_consumer


@asynccontextmanager
async def event_runtime(
    db_factory,
    *,
    poll_seconds: float = 2.0,
    enable_outbox: bool = True,
    consumer_group: str | None = None,
    handled_types: Set[str] | None = None,
    handler: Callable[[dict[str, Any]], None] | None = None,
):
    tasks: list[asyncio.Task] = []
    if enable_outbox:
        tasks.append(asyncio.create_task(outbox_poller(db_factory, poll_seconds)))
    if consumer_group and handled_types and handler:
        tasks.append(
            asyncio.create_task(
                kafka_event_consumer(
                    group_id=consumer_group,
                    handled_types=handled_types,
                    handler=handler,
                )
            )
        )
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
