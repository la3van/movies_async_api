"""PostgreSQL-репозиторий прав доступа."""
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_session import RefreshSession
from repositories.interfaces.refresh_session import RefreshSessionRepository


class PostgresRefreshSessionRepository(RefreshSessionRepository):
    """Реализует операции с refresh-сессиями в PostgreSQL."""
    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию PostgreSQL."""
        self.session = session

    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> RefreshSession | None:
        """Возвращает refresh-сессию по хешу токена или None,
        если она не найдена."""
        statement = (
            select(RefreshSession)
            .where(RefreshSession.token_hash == token_hash)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshSession:
        """Создаёт refresh-сессию и возвращает созданную модель."""
        refresh_session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.session.add(refresh_session)
        await self.session.flush()

        return refresh_session

    async def revoke(
        self,
        refresh_session: RefreshSession,
    ) -> RefreshSession:
        """Отзывает refresh-сессию и возвращает обновлённую запись."""
        refresh_session.revoked_at = datetime.now(timezone.utc)

        self.session.add(refresh_session)
        await self.session.flush()

        return refresh_session

    async def revoke_all_by_user_id(
        self,
        user_id: UUID,
        exclude_session_id: UUID | None = None,
    ) -> None:
        """Отзывает refresh-сессии пользователя."""
        statement = (
            update(RefreshSession)
            .where(RefreshSession.user_id == user_id)
            .where(RefreshSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

        if exclude_session_id is not None:
            statement = statement.where(
                RefreshSession.id != exclude_session_id
            )

        await self.session.execute(statement)
        await self.session.flush()
