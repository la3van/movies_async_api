"""Сервисный слой создания уведомлений."""

from uuid import UUID

from models.contract import Accepted, CreateNotification, TraceContext
from repositories.interfaces.notifications import NotificationsRepository


class NotificationService:
    """Приём заявки через интерфейс репозитория уведомлений."""

    def __init__(self, repository: NotificationsRepository) -> None:
        """Принимает реализацию интерфейса хранилища уведомлений."""
        self.repository = repository

    async def create(
        self,
        actor: UUID,
        key: str,
        request: CreateNotification,
        trace: TraceContext,
    ) -> Accepted:
        """Сохраняет заявку идемпотентно и возвращает её идентификаторы."""
        return await self.repository.create(actor, key, request, trace)
