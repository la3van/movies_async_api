"""Приём заданий Kafka с дедупликацией и обработкой DLQ."""

import asyncio
import base64
import json
import logging

from core.config import get_settings
from core.database import create_engine
from core.health import beat
from core.runtime import supervise
from models.contract import DeliveryJob
from pydantic import ValidationError
from repositories.interfaces.jobs import DeliveryConflict
from repositories.postgres.jobs import PostgresJobs
from services.ingestion import IngestionService
from sqlalchemy import text

from messaging.kafka import (
    ConsumerRecord,
    JobConsumer,
    Publisher,
    TopicPartition,
)

log = logging.getLogger(__name__)


async def handle(
    record: ConsumerRecord,
    service: IngestionService,
    publisher: Publisher,
    consumer: JobConsumer,
    dlq_topic: str,
) -> None:
    """Сохраняет задание или DLQ и лишь затем подтверждает offset."""
    try:
        job = DeliveryJob.model_validate_json(record.value or b"")
        await service.ingest(job)
    except (ValidationError, DeliveryConflict) as exc:
        envelope = json.dumps(
            {
                "schema_version": 1,
                "reason": type(exc).__name__,
                "source_topic": record.topic,
                "partition": record.partition,
                "offset": record.offset,
                "value_base64": base64.b64encode(record.value or b"").decode(),
                "key_base64": base64.b64encode(record.key or b"").decode(),
            }
        ).encode()
        await publisher.publish(
            dlq_topic,
            f"{record.topic}:{record.partition}:{record.offset}".encode(),
            envelope,
        )
    await consumer.commit(
        {TopicPartition(record.topic, record.partition): record.offset + 1}
    )


async def run(stop: asyncio.Event) -> None:
    """Принимает Kafka-задания и сохраняет их в базе воркера."""
    settings = get_settings()
    engine = create_engine(settings)
    publisher = Publisher(settings)
    consumer = JobConsumer(settings)
    service = IngestionService(PostgresJobs(engine))
    try:
        await publisher.start()
        await asyncio.wait_for(
            consumer.start(), settings.kafka_timeout_seconds
        )
        while not stop.is_set():
            await publisher.probe()
            record = await consumer.poll()
            if record is not None:
                await handle(
                    record, service, publisher, consumer, settings.dlq_topic
                )
            async with engine.connect() as conn:
                await conn.execute(
                    text("SELECT delivery_id FROM delivery_jobs LIMIT 0")
                )
            beat()
    finally:
        try:
            await consumer.stop()
        finally:
            try:
                await publisher.close()
            finally:
                await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
