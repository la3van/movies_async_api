"""Интерфейс репозитория социальных аккаунтов."""
from abc import ABC, abstractmethod
from uuid import UUID

from models.social_account import SocialAccount


class SocialAccountRepository(ABC):
    """Определяет операции с социальным аккаунтом."""
    @abstractmethod
    async def get_by_provider_identity(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ) -> SocialAccount | None:
        """Возвращает социальный аккаунт по данным провайдера."""
        pass  # pragma: no cover

    @abstractmethod
    async def create(
        self,
        *,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        email: str | None = None,
    ) -> SocialAccount:
        """Создаёт связь пользователя с OAuth-провайдером."""
        pass  # pragma: no cover
