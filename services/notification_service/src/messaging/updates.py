"""Приём событий кинотеатра и результатов отправки писем."""

import asyncio
import base64
import json
from uuid import NAMESPACE_URL, UUID, uuid5

from core.config import get_settings
from core.database import create_engine
from core.health import beat
from core.runtime import supervise
from models.contract import DeliveryJob, TraceContext
from models.management import CinemaEvent, DeliveryResult
from pydantic import ValidationError
from repositories.postgres.catalog import Catalog, enqueue
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from messaging.kafka import JobConsumer, Publisher, TopicPartition

SYSTEM = UUID("00000000-0000-4000-8000-000000000001")


async def apply(
    conn: AsyncConnection, raw: bytes, catalog: Catalog, kind: str
) -> None:
    """Применяет событие и дедупликацию inbox в переданной транзакции."""
    event = (
        DeliveryResult if kind == "results" else CinemaEvent
    ).model_validate_json(raw)
    inserted = (
        await conn.execute(
            text(
                (
                    "INSERT INTO inbox(event_id) VALUES (:id) ON "
                    "CONFLICT DO NOTHING RETURNING event_id"
                )
            ),
            dict(id=event.event_id),
        )
    ).scalar_one_or_none()
    if inserted is None:
        return
    if isinstance(event, DeliveryResult):
        await conn.execute(
            text("""
            UPDATE notifications SET
status=:state,attempt=:attempt,error_code=:error,updated_at=now()
            WHERE id=:id AND delivery_id=:delivery AND
attempt<:attempt AND status!='sent'
"""),
            dict(
                state=event.status,
                attempt=event.attempt,
                error=event.error_code,
                id=event.notification_id,
                delivery=event.delivery_id,
            ),
        )
        return
    template_id = (
        await conn.execute(
            text("SELECT id FROM templates WHERE name=:name AND NOT archived"),
            dict(name=event.kind),
        )
    ).scalar_one_or_none()
    if template_id is None:
        raise RuntimeError("System template unavailable")
    snapshot = await catalog.snapshot(conn, template_id)
    identity = uuid5(NAMESPACE_URL, "cinema-event:" + str(event.event_id))
    if event.kind == "user.registered":
        job = DeliveryJob(
            user_id=event.aggregate_id,
            template=snapshot,
            notification_id=identity,
            delivery_id=uuid5(identity, "email"),
            event_id=uuid5(identity, "delivery"),
            trace_context=TraceContext(request_id=str(event.event_id)),
        )
        await enqueue(
            conn, job, SYSTEM, str(event.event_id), catalog.settings.jobs_topic
        )
    else:
        request = {
            "context": {
                "film_id": str(event.aggregate_id),
                "film_title": event.title or "",
            }
        }
        await conn.execute(
            text("""
            INSERT INTO
campaigns(id,actor_id,idempotency_key,request,snapshot)
            VALUES (:id,:actor,:key,CAST(:request AS
JSONB),CAST(:snapshot AS JSONB))
            ON CONFLICT(actor_id,idempotency_key) DO NOTHING
"""),
            dict(
                id=identity,
                actor=SYSTEM,
                key=str(event.event_id),
                request=json.dumps(request),
                snapshot=snapshot.model_dump_json(),
            ),
        )


async def run(stop: asyncio.Event, kind: str = "results") -> None:
    """Читает события или результаты и подтверждает их после обработки."""
    settings = get_settings()
    topic = (
        settings.results_topic if kind == "results" else settings.events_topic
    )
    consumer = JobConsumer(
        settings.model_copy(
            update={
                "jobs_topic": topic,
                "consumer_group": "notifications-" + kind + "-v1",
            }
        )
    )
    publisher = Publisher(settings.model_copy(update={"jobs_topic": topic}))
    engine = create_engine(settings)
    catalog = Catalog(engine, settings)
    try:
        await publisher.start()
        await consumer.start()
        while not stop.is_set():
            await publisher.probe()
            record = await consumer.poll()
            if record:
                try:
                    async with engine.begin() as conn:
                        await apply(conn, record.value or b"", catalog, kind)
                except ValidationError:
                    envelope = dict(
                        source_topic=record.topic,
                        partition=record.partition,
                        offset=record.offset,
                        reason="invalid_" + kind,
                        value_base64=base64.b64encode(
                            record.value or b""
                        ).decode(),
                    )
                    await publisher.publish(
                        settings.dlq_topic,
                        f"{record.topic}:{record.partition}:{record.offset}".encode(),
                        json.dumps(envelope).encode(),
                    )
                await consumer.commit(
                    {
                        TopicPartition(
                            record.topic, record.partition
                        ): record.offset + 1
                    }
                )
            beat()
    finally:
        try:
            await consumer.stop()
            await publisher.close()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    import sys

    kind = sys.argv[1] if len(sys.argv) > 1 else "results"
    asyncio.run(supervise(lambda stop: run(stop, kind)))
