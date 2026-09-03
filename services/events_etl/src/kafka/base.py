"""Базовые модели и интерфейсы чтения пользовательских событий."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ConsumedMessage:
    """Полученное событие вместе с метаданными источника."""

    value: bytes | None
    topic: str
    partition: int
    offset: int


@dataclass(frozen=True)
class RejectedMessage:
    """Kafka-сообщение, которое ETL не смог преобразовать."""

    message: ConsumedMessage
    error_type: str
    error_message: str


class EventConsumer(Protocol):
    """Интерфейс получения пользовательских событий."""

    def subscribe(self) -> None:
        """Подписаться на источник событий."""
        # no pragma

    def poll_batch(self) -> list[ConsumedMessage]:
        """Получить очередной пакет событий."""
        # no pragma

    def commit_offsets(
        self,
        messages: list[ConsumedMessage],
    ) -> None:
        """Подтвердить успешно обработанный пакет."""
        # no pragma

    def close(self) -> None:
        """Корректно завершить работу consumer."""
        # no pragma


class DeadLetterPublisher(Protocol):
    """Интерфейс публикации некорректных событий в DLQ."""

    def publish_batch(
        self,
        messages: list[RejectedMessage],
    ) -> None:
        """Надёжно опубликовать пакет сообщений в DLQ."""
        ...

    def close(self) -> None:
        """Корректно завершить publisher."""
        ...
