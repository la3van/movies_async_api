"""Интерфейс репозитория истории входов."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from models.login_history import LoginHistory


class LoginHistoryRepository(ABC):
    """Определяет операции получения и сохранения истории входов."""

    @abstractmethod
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
        # pragma: no cover

    @abstractmethod
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
        # pragma: no cover
