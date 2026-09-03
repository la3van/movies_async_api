"""PostgreSQL-репозиторий истории входов."""

from datetime import datetime
from uuid import UUID

from models.login_history import LoginHistory
from repositories.interfaces.login_history import LoginHistoryRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PostgresLoginHistoryRepository(LoginHistoryRepository):
    """Реализует операции с login-history в PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию PostgreSQL."""
        self.session = session

    async def get_by_user_id(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[LoginHistory]:
        """Возвращает историю входов пользователя."""
        statement = select(LoginHistory).where(
            LoginHistory.user_id == user_id,
        )

        if created_from is not None:
            statement = statement.where(
                LoginHistory.created_at >= created_from,
            )
        if created_to is not None:
            statement = statement.where(
                LoginHistory.created_at < created_to,
            )

        statement = (
            statement.order_by(
                LoginHistory.created_at.desc(),
                LoginHistory.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        login: str,
        is_successful: bool,
        user_id: UUID | None = None,
        reason: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> LoginHistory:
        """Создаёт запись истории входа и возвращает созданную модель."""
        login_history = LoginHistory(
            login=login,
            is_successful=is_successful,
            user_id=user_id,
            reason=reason,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        self.session.add(login_history)
        await self.session.flush()

        return login_history
