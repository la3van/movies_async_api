"""Публикация outbox в Kafka с подтверждением доставки."""

import asyncio
import json
import logging

from core.config import get_settings
from core.database import create_engine
from core.health import beat, unready
from core.runtime import pause, supervise
from core.telemetry import OPERATIONS, span
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from messaging.kafka import Publisher


async def publish_one(engine: AsyncEngine, publisher: Publisher) -> bool:
    """Публикует одну запись outbox и отмечает её после ACK Kafka."""
    async with engine.begin() as conn:
        row = (
            (
                await conn.execute(
                    text("""
            SELECT event_id, topic, message_key, payload FROM
outbox
            WHERE published_at IS NULL ORDER BY created_at,
event_id
            FOR UPDATE SKIP LOCKED LIMIT 1
""")
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return False
        with span("outbox.publish"):
            await publisher.publish(
                row["topic"],
                row["message_key"].encode(),
                json.dumps(row["payload"]).encode(),
            )
        await conn.execute(
            text("UPDATE outbox SET published_at=now() WHERE event_id=:id"),
            {"id": row["event_id"]},
        )
    OPERATIONS.labels("outbox", "published").inc()
    return True


async def run(stop: asyncio.Event) -> None:
    """Публикует ожидающий outbox, повторяя итерации после ошибок."""
    settings = get_settings()
    engine = create_engine(settings)
    producer = Publisher(settings)
    try:
        await producer.start()
        while not stop.is_set():
            try:
                await producer.probe()
                sent = await publish_one(engine, producer)
                beat()
                if not sent:
                    await pause(stop, settings.poll_seconds)
            except Exception:
                unready()
                OPERATIONS.labels("outbox", "error").inc()
                logging.getLogger(__name__).error("Outbox publication failed")
                await pause(stop, settings.poll_seconds)
    finally:
        try:
            await producer.close()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
