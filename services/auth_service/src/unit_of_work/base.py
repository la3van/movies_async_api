"""Абстракция Unit of Work."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType

from repositories.interfaces import (
    LoginHistoryRepository,
    PermissionRepository,
    RefreshSessionRepository,
    RoleRepository,
    SocialAccountRepository,
    UserRepository,
)
from repositories.interfaces.notification import (
    NotificationAudienceRepository,
)


class AbstractUnitOfWork(ABC):
    """Определяет границы одной бизнес-транзакции."""

    notification_audiences: NotificationAudienceRepository
    users: UserRepository
    roles: RoleRepository
    permissions: PermissionRepository
    refresh_sessions: RefreshSessionRepository
    login_history: LoginHistoryRepository
    social_accounts: SocialAccountRepository

    @abstractmethod
    async def __aenter__(self) -> "AbstractUnitOfWork":
        """Открывает UoW и инициализирует репозитории."""
        # pragma: no cover

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Освобождает ресурсы и откатывает транзакцию при ошибке."""
        # pragma: no cover

    @abstractmethod
    async def commit(self) -> None:
        """Фиксирует изменения текущей транзакции."""
        # pragma: no cover

    @abstractmethod
    async def rollback(self) -> None:
        """Откатывает изменения текущей транзакции."""
        # pragma: no cover


UnitOfWorkFactory = Callable[[], AbstractUnitOfWork]
