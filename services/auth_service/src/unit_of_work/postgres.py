"""SQLAlchemy-реализация Unit of Work."""

from types import TracebackType

from repositories.postgres.login_history import (
    PostgresLoginHistoryRepository,
)
from repositories.postgres.permission import (
    PostgresPermissionRepository,
)
from repositories.postgres.refresh_session import (
    PostgresRefreshSessionRepository,
)
from repositories.postgres.role import PostgresRoleRepository
from repositories.postgres.social_account import (
    PostgresSocialAccountRepository,
)
from repositories.postgres.user import PostgresUserRepository
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from unit_of_work.base import AbstractUnitOfWork


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """Управляет общей SQLAlchemy-сессией и репозиториями."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Сохраняет фабрику SQLAlchemy-сессий."""
        self._session_factory = session_factory
        self.session: AsyncSession

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """Создаёт сессию и репозитории для одной бизнес операции."""
        self.session = self._session_factory()

        self.users = PostgresUserRepository(self.session)
        self.roles = PostgresRoleRepository(self.session)
        self.permissions = PostgresPermissionRepository(self.session)
        self.refresh_sessions = PostgresRefreshSessionRepository(
            self.session,
        )
        self.login_history = PostgresLoginHistoryRepository(
            self.session,
        )
        self.social_accounts = PostgresSocialAccountRepository(
            self.session,
        )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Откатывает транзакцию при ошибке и закрывает сессию."""
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self.session.close()

    async def commit(self) -> None:
        """Фиксирует изменения текущей транзакции."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Откатывает изменения текущей транзакции."""
        await self.session.rollback()
