"""Базовые интерфейсы публикации пользовательских событий."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DeliveryMetadata:
    """Метаданные успешно опубликованного сообщения Kafka."""

    topic: str
    partition: int
    offset: int


class EventPublisher(Protocol):
    """Интерфейс публикации пользовательских событий."""

    def publish(
        self,
        *,
        key: str,
        value: bytes,
        event_type: str,
        request_id: str,
        schema_version: int,
    ) -> DeliveryMetadata:
        """Опубликовать событие и дождаться подтверждения Kafka."""
        # pragma: no cover

    def is_ready(self) -> bool:
        """Проверить доступность Kafka и целевого топика."""
        # pragma: no cover

    def close(self) -> None:
        """Корректно завершить работу publisher."""
        # pragma: no cover
