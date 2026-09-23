"""Интерфейс хранилища заданий и ошибка коллизии доставки."""

from typing import Protocol

from models.contract import DeliveryJob


class DeliveryConflict(Exception):
    """Один delivery_id не может обозначать разные задания."""


class JobsRepository(Protocol):
    """Контракт сохранения заданий до подтверждения Kafka."""

    async def save(self, job: DeliveryJob) -> None:
        """Сохраняет задание, отклоняя другой payload с тем же delivery_id."""
        ...
