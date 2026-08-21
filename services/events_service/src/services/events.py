"""Сервис обработки и публикации пользовательских событий."""
import logging
from datetime import datetime, timezone
from uuid import UUID

import orjson

from kafka.base import (
    DeliveryMetadata,
    EventPublisher,
)
from kafka.exceptions import KafkaPublishError
from models.events import EventRequest
from services.exceptions import EventIngestionUnavailable

logger = logging.getLogger(__name__)


class EventService:
    """Обрабатывает пользовательские события и публикует их в Kafka."""
    def __init__(
        self,
        publisher: EventPublisher,
    ) -> None:
        """Создать сервис обработки событий."""
        self._publisher = publisher

    def ingest(
        self,
        *,
        event: EventRequest,
        trusted_user_id: UUID,
        request_id: str,
    ) -> DeliveryMetadata:
        """Подготовить событие и опубликовать его в Kafka."""
        received_at = datetime.now(
            timezone.utc,
        )

        message = event.model_dump(
            mode="json",
        )

        message["user_id"] = str(
            trusted_user_id
        )

        message["received_at"] = (
            received_at
            .isoformat()
            .replace(
                "+00:00",
                "Z",
            )
        )
        message["request_id"] = request_id

        serialized_event = orjson.dumps(
            message,
        )

        try:
            metadata = self._publisher.publish(
                key=str(event.session_id),
                value=serialized_event,
                event_type=event.event_type,
                request_id=request_id,
                schema_version=event.schema_version,
            )
        except KafkaPublishError as exc:
            logger.exception(
                "Не удалось опубликовать пользовательское событие: "
                "event_id=%s event_type=%s",
                event.event_id,
                event.event_type,
            )

            raise EventIngestionUnavailable(
                "Система приёма пользовательских событий "
                "временно недоступна"
            ) from exc

        logger.info(
            "Пользовательское событий опубликовано: "
            "event_id=%s "
            "event_type=%s "
            "topic=%s "
            "partition=%s "
            "offset=%s",
            event.event_id,
            event.event_type,
            metadata.topic,
            metadata.partition,
            metadata.offset,
        )

        return metadata

    def is_ready(self) -> bool:
        """Проверить готовность внешних зависимостей сервиса."""
        return self._publisher.is_ready()
