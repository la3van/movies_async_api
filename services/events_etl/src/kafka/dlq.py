"""Публикация некорректных пользовательских событий в Kafka DLQ."""
import base64
import logging
from datetime import datetime, timezone

import orjson
from confluent_kafka import (
    KafkaError,
    KafkaException,
    Message,
    Producer,
)

from core.config import Settings
from kafka.base import RejectedMessage
from kafka.exceptions import KafkaDeadLetterPublishError

logger = logging.getLogger(__name__)


class KafkaDeadLetterPublisher:
    """Надёжно публикует отклонённые события в DLQ."""
    def __init__(
        self,
        *,
        settings: Settings,
        producer: Producer | None = None,
    ) -> None:
        """Создать Kafka DLQ Producer."""
        self._settings = settings
        self._topic = settings.kafka_dlq_topic
        self._producer = (
            producer
            or Producer(
                settings.kafka_dlq_producer_config
            )
        )

    def publish_batch(
        self,
        messages: list[RejectedMessage],
    ) -> None:
        """Опубликовать пакет и дождаться подтверждения Kafka."""
        if not messages:
            return

        delivery_errors: list[str] = []

        def on_delivery(
            error: KafkaError | None,
            message: Message,
        ) -> None:
            if error is not None:
                delivery_errors.append(str(error))

        try:
            for rejected in messages:
                source = rejected.message

                self._producer.produce(
                    topic=self._topic,
                    key=(
                        f"{source.topic}:"
                        f"{source.partition}:"
                        f"{source.offset}"
                    ),
                    value=self._serialize(rejected),
                    on_delivery=on_delivery,
                )

            remaining = self._producer.flush(
                self._settings
                .kafka_dlq_flush_timeout_seconds
            )
        except (BufferError, KafkaException) as exc:
            raise KafkaDeadLetterPublishError(
                "Не удалось отправить сообщения в Kafka DLQ"
            ) from exc

        if remaining:
            raise KafkaDeadLetterPublishError(
                "Не все сообщения были подтверждены Kafka DLQ: "
                f"remaining={remaining}"
            )

        if delivery_errors:
            raise KafkaDeadLetterPublishError(
                "Kafka DLQ вернула ошибку доставки: "
                f"{delivery_errors[0]}"
            )

        logger.info(
            "Сообщения успешно опубликованы в DLQ: "
            "topic=%s count=%s",
            self._topic,
            len(messages),
        )

    @staticmethod
    def _serialize(
        rejected: RejectedMessage,
    ) -> bytes:
        """Сериализовать ошибку и исходный payload без потери bytes."""
        source = rejected.message

        payload_base64 = (
            base64.b64encode(
                source.value
            ).decode("ascii")
            if source.value is not None
            else None
        )

        failed_at = (
            datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        return orjson.dumps(
            {
                "failed_at": failed_at,
                "error": {
                    "type": rejected.error_type,
                    "message": rejected.error_message,
                },
                "source": {
                    "topic": source.topic,
                    "partition": source.partition,
                    "offset": source.offset,
                },
                "payload_base64": payload_base64,
            }
        )

    def close(self) -> None:
        """Дождаться оставшихся сообщений при shutdown."""
        remaining = self._producer.flush(
            self._settings
            .kafka_dlq_flush_timeout_seconds
        )

        if remaining:
            logger.warning(
                "При закрытии DLQ Producer остались "
                "неподтверждённые сообщения: count=%s",
                remaining,
            )
