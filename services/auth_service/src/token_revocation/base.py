"""Интерфейс хранилища отозванных access-токенов."""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID


class AccessTokenRevocationStore(ABC):
    """Определяет операции отзыва access-токенов."""
    @abstractmethod
    async def revoke_token(
        self,
        token_id: UUID,
        expires_at: datetime,
    ) -> None:
        """Отзывает один access-токен до его истечения."""
        pass  # pragma: no cover

    @abstractmethod
    async def revoke_sessions(
        self,
        session_ids: Sequence[UUID],
    ) -> None:
        """Отзывает access-токены указанных сессий."""
        pass  # pragma: no cover

    @abstractmethod
    async def is_revoked(
        self,
        token_id: UUID,
        session_id: UUID,
    ) -> bool:
        """Проверяет отзыв токена или всей его сессии."""
        pass  # pragma: no cover
