"""Интерфейс хранилища заявок и ошибка идемпотентности."""

from typing import Protocol
from uuid import UUID

from models.contract import Accepted, CreateNotification, TraceContext


class IdempotencyConflict(Exception):
    """Повтор ключа идемпотентности с другим содержимым."""

    pass


class NotificationsRepository(Protocol):
    """Контракт транзакционного сохранения уведомлений."""

    async def create(
        self,
        actor: UUID,
        key: str,
        request: CreateNotification,
        trace: TraceContext,
    ) -> Accepted:
        """Сохраняет заявку идемпотентно и возвращает её идентификаторы."""
        ...
