"""Интерфейс хранения снимков аудитории уведомлений."""

from abc import ABC, abstractmethod
from uuid import UUID


class NotificationAudienceRepository(ABC):
    """Определяет операции с неизменяемой аудиторией рассылки."""

    @abstractmethod
    async def create_snapshot(self, audience_id: UUID) -> None:
        """Сохраняет активных получателей при первом создании снимка."""

    @abstractmethod
    async def get_page(
        self,
        audience_id: UUID,
        after: UUID | None,
        limit: int,
    ) -> list[UUID] | None:
        """Возвращает страницу либо None, если снимок отсутствует."""
