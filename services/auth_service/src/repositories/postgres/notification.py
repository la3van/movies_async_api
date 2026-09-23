"""PostgreSQL-репозиторий снимков аудитории уведомлений."""

from uuid import UUID

from repositories.interfaces.notification import (
    NotificationAudienceRepository,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class PostgresNotificationAudienceRepository(NotificationAudienceRepository):
    """Сохраняет и постранично читает состав массовой рассылки."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию текущей бизнес-транзакции."""
        self.session = session

    async def create_snapshot(self, audience_id: UUID) -> None:
        """Создаёт снимок один раз, не меняя аудиторию при повторе."""
        result = await self.session.execute(
            text(
                """
                INSERT INTO notification_audiences(id)
                VALUES (:id)
                ON CONFLICT DO NOTHING
                RETURNING id
                """
            ),
            {"id": audience_id},
        )
        if result.scalar_one_or_none() is None:
            return

        await self.session.execute(
            text(
                """
                INSERT INTO notification_audience_members(
                    audience_id, user_id
                )
                SELECT :id, id FROM users WHERE is_active
                """
            ),
            {"id": audience_id},
        )

    async def get_page(
        self,
        audience_id: UUID,
        after: UUID | None,
        limit: int,
    ) -> list[UUID] | None:
        """Возвращает следующую страницу в порядке UUID."""
        result = await self.session.execute(
            text("SELECT id FROM notification_audiences WHERE id = :id"),
            {"id": audience_id},
        )
        if result.scalar_one_or_none() is None:
            return None

        rows = await self.session.execute(
            text(
                """
                SELECT user_id
                FROM notification_audience_members
                WHERE audience_id = :id
                  AND (CAST(:after AS UUID) IS NULL OR user_id > :after)
                ORDER BY user_id
                LIMIT :limit
                """
            ),
            {"id": audience_id, "after": after, "limit": limit},
        )
        return [UUID(str(item)) for item in rows.scalars()]
