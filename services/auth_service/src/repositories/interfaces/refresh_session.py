"""Интерфейс репозитория refresh-сессий."""
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from models.refresh_session import RefreshSession


class RefreshSessionRepository(ABC):
    """Определяет операции получения и сохранения refresh-сессий."""
    @abstractmethod
    async def get_by_token_hash(
        self,
        token_hash: str,
    ) -> RefreshSession | None:
        """Возвращает refresh-сессию по хешу токена или None,
        если она не найдена."""
        pass  # pragma: no cover

    @abstractmethod
    async def create(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> RefreshSession:
        """Создаёт refresh-сессию и возвращает созданную модель."""
        pass  # pragma: no cover

    @abstractmethod
    async def revoke(
        self,
        refresh_session: RefreshSession,
    ) -> RefreshSession:
        """Отзывает refresh-сессию и возвращает обновлённую запись."""
        pass  # pragma: no cover

    @abstractmethod
    async def revoke_all_by_user_id(
        self,
        user_id: UUID,
        exclude_session_id: UUID | None = None,
    ) -> list[UUID]:
        """Отзывает сессии и возвращает их идентификаторы."""
        pass  # pragma: no cover
