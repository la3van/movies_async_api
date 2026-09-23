"""Сохранение входящих заданий с уникальным delivery_id."""

from models.contract import DeliveryJob
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from repositories.interfaces.jobs import DeliveryConflict


class PostgresJobs:
    """Хранилище принятых заданий с проверкой коллизий."""

    def __init__(self, engine: AsyncEngine) -> None:
        """Сохраняет пул соединений для входящих заданий."""
        self.engine = engine

    async def save(self, job: DeliveryJob) -> None:
        """Сохраняет задание, отклоняя другой payload с тем же delivery_id."""
        async with self.engine.begin() as conn:
            result = await conn.execute(
                text("""
                INSERT INTO delivery_jobs
                    (delivery_id, event_id, notification_id,
payload)
                VALUES (:delivery, :event, :notification,
                        CAST(:payload AS JSONB))
                ON CONFLICT (delivery_id) DO NOTHING RETURNING
delivery_id
"""),
                dict(
                    delivery=job.delivery_id,
                    event=job.event_id,
                    notification=job.notification_id,
                    payload=job.model_dump_json(),
                ),
            )
            if result.scalar_one_or_none() is None:
                payload = (
                    await conn.execute(
                        text(
                            "SELECT payload FROM delivery_jobs "
                            "WHERE delivery_id=:id"
                        ),
                        {"id": job.delivery_id},
                    )
                ).scalar_one()
                if DeliveryJob.model_validate(payload) != job:
                    raise DeliveryConflict
