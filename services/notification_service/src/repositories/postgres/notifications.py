"""Транзакционное сохранение уведомления вместе с outbox."""

import json
from uuid import UUID, uuid4

from core.config import get_settings
from models.contract import (
    Accepted,
    CreateNotification,
    DeliveryJob,
    TraceContext,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from repositories.interfaces.notifications import IdempotencyConflict


class PostgresNotifications:
    """Хранилище заявок с дедупликацией на стороне PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Сохраняет пул соединений для транзакций уведомлений."""
        self.engine = engine

    async def create(
        self,
        actor: UUID,
        key: str,
        request: CreateNotification,
        trace: TraceContext,
    ) -> Accepted:
        """Сохраняет заявку идемпотентно и возвращает её идентификаторы."""
        notification_id, delivery_id, event_id = uuid4(), uuid4(), uuid4()
        payload = request.model_dump(mode="json")
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("""
                INSERT INTO notifications
                    (id, delivery_id, actor_id, idempotency_key,
request)
                VALUES (:id, :delivery, :actor, :key,
CAST(:request AS JSONB))
                ON CONFLICT (actor_id, idempotency_key) DO
NOTHING
                RETURNING id
"""),
                dict(
                    id=notification_id,
                    delivery=delivery_id,
                    actor=actor,
                    key=key,
                    request=json.dumps(payload),
                ),
            )
            if result.scalar_one_or_none() is None:
                row = (
                    (
                        await conn.execute(
                            text("""
                    SELECT id, delivery_id, request FROM
notifications
                    WHERE actor_id=:actor AND
idempotency_key=:key
"""),
                            dict(actor=actor, key=key),
                        )
                    )
                    .mappings()
                    .one()
                )
                if (
                    CreateNotification.model_validate(row["request"])
                    != request
                ):
                    raise IdempotencyConflict
                return Accepted(
                    notification_id=row["id"], delivery_id=row["delivery_id"]
                )
            job = DeliveryJob(
                **request.model_dump(),
                event_id=event_id,
                notification_id=notification_id,
                delivery_id=delivery_id,
                trace_context=trace,
            )
            await conn.execute(
                text("""
                INSERT INTO outbox(event_id, notification_id,
payload, topic, message_key)
                VALUES (:event, :notification, CAST(:payload AS
JSONB), :topic, :key)
"""),
                dict(
                    event=event_id,
                    notification=notification_id,
                    payload=job.model_dump_json(),
                    topic=get_settings().jobs_topic,
                    key=str(delivery_id),
                ),
            )
        return Accepted(
            notification_id=notification_id, delivery_id=delivery_id
        )
