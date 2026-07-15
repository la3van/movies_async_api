"""Абстракция Unit of Work."""
from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType

from repositories.interfaces import (
    LoginHistoryRepository,
    PermissionRepository,
    RefreshSessionRepository,
    RoleRepository,
    UserRepository,
)


class AbstractUnitOfWork(ABC):
    """Определяет границы одной бизнес-транзакции."""
    users: UserRepository
    roles: RoleRepository
    permissions: PermissionRepository
    refresh_sessions: RefreshSessionRepository
    login_history: LoginHistoryRepository

    @abstractmethod
    async def __aenter__(self) -> 'AbstractUnitOfWork':
        """Открывает UoW и инициализирует репозитории."""
        pass  # pragma: no cover

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Освобождает ресурсы и откатывает транзакцию при ошибке."""
        pass  # pragma: no cover

    @abstractmethod
    async def commit(self) -> None:
        """Фиксирует изменения текущей транзакции."""
        pass  # pragma: no cover

    @abstractmethod
    async def rollback(self) -> None:
        """Откатывает изменения текущей транзакции."""
        pass  # pragma: no cover


UnitOfWorkFactory = Callable[[], AbstractUnitOfWork]
