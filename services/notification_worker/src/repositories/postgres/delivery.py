"""Захват заданий, фиксация попыток и результатов отправки."""

import json
from typing import Any
from uuid import UUID, uuid4

from core.config import Settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DeliveryRepository:
    """Хранилище аренды заданий и результатов SMTP-попыток."""

    def __init__(self, engine: AsyncEngine, settings: Settings) -> None:
        """Сохраняет пул PostgreSQL и параметры аренды заданий."""
        self.engine, self.settings = engine, settings

    async def claim(self) -> dict[str, Any] | None:
        """Захватывает задание и фиксирует аренду до обращения к сети."""
        async with self.engine.begin() as conn:
            row = (
                (
                    await conn.execute(
                        text("""
                SELECT * FROM delivery_jobs
                WHERE (status IN ('pending','retry') AND
next_attempt_at<=now())
                   OR (status='processing' AND lease_until<now())
                ORDER BY next_attempt_at FOR UPDATE SKIP LOCKED
LIMIT 1
""")
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            token = uuid4()
            result = await conn.execute(
                text("""
                UPDATE delivery_jobs SET status='processing',
attempt=attempt+1,
                    claim_token=:token,
lease_until=now()+make_interval(secs=>:lease),
                    updated_at=now()
                WHERE delivery_id=:id RETURNING *
"""),
                dict(
                    token=token,
                    lease=self.settings.lease_seconds,
                    id=row["delivery_id"],
                ),
            )
            return dict(result.mappings().one())

    async def finish(
        self,
        row: dict[str, Any],
        state: str,
        error: str | None,
        delay: float = 0,
    ) -> bool:
        """Фиксирует результат и outbox только для действующего claim_token."""
        event_id = uuid4()
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("""
                UPDATE delivery_jobs SET status=:state,
error_code=:error,
next_attempt_at=now()+make_interval(secs=>:delay),
                    lease_until=NULL, claim_token=NULL,
updated_at=now()
                WHERE delivery_id=:id AND claim_token=:token
                RETURNING delivery_id
"""),
                dict(
                    state=state,
                    error=error,
                    delay=delay,
                    id=row["delivery_id"],
                    token=row["claim_token"],
                ),
            )
            if result.scalar_one_or_none() is None:
                return False
            event = dict(
                schema_version=1,
                event_id=str(event_id),
                delivery_id=str(row["delivery_id"]),
                notification_id=str(row["notification_id"]),
                status=state,
                attempt=row["attempt"],
                error_code=error,
            )
            # Результат и событие меняются одной транзакцией; API узнает
            # статус даже при падении отправителя сразу после commit.
            await conn.execute(
                text("""
                INSERT INTO
outbox(event_id,topic,message_key,payload)
                VALUES (:id,:topic,:key,CAST(:payload AS JSONB))
"""),
                dict(
                    id=event_id,
                    topic=self.settings.results_topic,
                    key=str(row["delivery_id"]),
                    payload=json.dumps(event),
                ),
            )
            if state == "failed":
                failure = {
                    **event,
                    "event_id": str(uuid4()),
                    "job": row["payload"],
                }
                await conn.execute(
                    text("""
                    INSERT INTO
outbox(event_id,topic,message_key,payload)
                    VALUES (:id,:topic,:key,CAST(:payload AS
JSONB))
"""),
                    dict(
                        id=UUID(failure["event_id"]),
                        topic=self.settings.failed_topic,
                        key=str(row["delivery_id"]),
                        payload=json.dumps(failure),
                    ),
                )
        return True
