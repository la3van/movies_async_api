"""Запускается отдельным процессом у источника с его DB-настройками."""

import asyncio
import json

from core.config import get_settings
from core.health import beat
from core.runtime import pause, supervise
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import create_async_engine

from messaging.kafka import Publisher


class SourceSettings(BaseSettings):
    """Параметры PostgreSQL сервиса — источника событий."""

    model_config = SettingsConfigDict(extra="ignore")
    postgres_host: str
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr


async def run(stop: asyncio.Event) -> None:
    """Переносит события источника в Kafka с отметкой после ACK."""
    settings = get_settings()
    source = SourceSettings()
    engine = create_async_engine(
        URL.create(
            "postgresql+asyncpg",
            username=source.postgres_user,
            password=source.postgres_password.get_secret_value(),
            host=source.postgres_host,
            port=source.postgres_port,
            database=source.postgres_db,
        ),
        pool_pre_ping=True,
        connect_args={"timeout": 5, "command_timeout": 30},
    )
    producer = Publisher(
        settings.model_copy(update={"jobs_topic": settings.events_topic})
    )
    try:
        await producer.start()
        while not stop.is_set():
            await producer.probe()
            async with engine.begin() as conn:
                row = (
                    (
                        await conn.execute(
                            text(
                                (
                                    "SELECT event_id,payload FROM "
                                    "public.notification_events WHERE "
                                    "published_at "
                                    "IS NULL ORDER BY created_at,event_id FOR "
                                    "UPDATE SKIP LOCKED LIMIT 1"
                                )
                            )
                        )
                    )
                    .mappings()
                    .first()
                )
                if row:
                    await producer.publish(
                        settings.events_topic,
                        str(row["event_id"]).encode(),
                        json.dumps(row["payload"]).encode(),
                    )
                    await conn.execute(
                        text(
                            (
                                "UPDATE public.notification_events SET "
                                "published_at=now() WHERE event_id=:id"
                            )
                        ),
                        dict(id=row["event_id"]),
                    )
            beat()
            if row is None:
                await pause(stop, settings.poll_seconds)
    finally:
        try:
            await producer.close()
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
