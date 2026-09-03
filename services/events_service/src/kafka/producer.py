"""Публикация пользовательских событий в Kafka."""

from __future__ import annotations

import logging
from typing import Any

import gevent
from confluent_kafka import (
    KafkaError,
    KafkaException,
    Message,
    Producer,
)
from core.config import Settings
from gevent import get_hub
from gevent.event import AsyncResult, Event
from gevent.timeout import Timeout
from kafka.base import DeliveryMetadata
from kafka.exceptions import (
    KafkaPublisherClosed,
    KafkaPublishError,
    KafkaPublishTimeout,
    KafkaQueueFull,
)
from opentelemetry.instrumentation.confluent_kafka import (
    ConfluentKafkaInstrumentor,
)
from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger(__name__)


class KafkaEventPublisher:
    """Публикует пользовательские события в Kafka."""

    def __init__(
        self,
        settings: Settings,
        tracer_provider: TracerProvider | None = None,
    ) -> None:
        """Создать Kafka Producer и запустить обработчик callback-событий."""
        self._settings = settings
        self._topic = settings.kafka_topic
        self._closed = False

        raw_producer = Producer(
            settings.kafka_producer_config,
        )
        self._raw_producer = raw_producer

        if tracer_provider is not None:
            self._producer: Any = (
                ConfluentKafkaInstrumentor.instrument_producer(
                    raw_producer,
                    tracer_provider=tracer_provider,
                )
            )
        else:
            self._producer = raw_producer

        self._stop_event = Event()
        self._poller = gevent.spawn(
            self._poll_loop,
        )

    def publish(
        self,
        *,
        key: str,
        value: bytes,
        event_type: str,
        request_id: str,
        schema_version: int,
    ) -> DeliveryMetadata:
        """Опубликовать сообщение и дождаться результата доставки."""
        if self._closed:
            raise KafkaPublisherClosed("Kafka Publisher уже завершил работу")

        delivery_result: AsyncResult[DeliveryMetadata] = AsyncResult()

        def on_delivery(
            error: KafkaError | None,
            message: Message,
        ) -> None:
            """Обработать результат доставки конкретного сообщения."""
            if delivery_result.ready():
                return

            if error is not None:
                delivery_result.set_exception(
                    KafkaPublishError(
                        f"Ошибка доставки сообщения Kafka: {error}"
                    )
                )
                return

            topic = message.topic()
            partition = message.partition()
            offset = message.offset()

            if topic is None or partition is None or offset is None:
                delivery_result.set_exception(
                    KafkaPublishError(
                        "Kafka returned incomplete delivery metadata"
                    )
                )
                return

            delivery_result.set(
                DeliveryMetadata(
                    topic=topic,
                    partition=partition,
                    offset=offset,
                )
            )

        headers = [
            (
                "content-type",
                b"application/json",
            ),
            (
                "x-request-id",
                request_id.encode("utf-8"),
            ),
            (
                "event-type",
                event_type.encode("utf-8"),
            ),
            (
                "schema-version",
                str(schema_version).encode("utf-8"),
            ),
        ]

        try:
            self._producer.produce(
                topic=self._topic,
                key=key,
                value=value,
                headers=headers,
                on_delivery=on_delivery,
            )
        except BufferError as exc:
            raise KafkaQueueFull(
                "Локальная очередь Kafka Producer переполнена"
            ) from exc
        except KafkaException as exc:
            raise KafkaPublishError(
                "Не удалось передать сообщение Kafka Producer"
            ) from exc

        try:
            metadata = delivery_result.get(
                timeout=self._settings.kafka_ack_timeout_seconds,
            )
        except Timeout as exc:
            raise KafkaPublishTimeout(
                "Не получено подтверждение доставки Kafka за отведённое время"
            ) from exc

        if metadata is None:
            raise KafkaPublishError(
                "Kafka delivery callback returned no metadata"
            )

        return metadata

    def is_ready(self) -> bool:
        """Проверить доступность Kafka и наличие целевого топика."""
        if self._closed:
            return False

        try:
            metadata = (
                get_hub()
                .threadpool.spawn(
                    self._raw_producer.list_topics,
                    self._topic,
                    self._settings.kafka_metadata_timeout_seconds,
                )
                .get()
            )
        except KafkaException:
            logger.exception("Не удалось получить метаданные Kafka")
            return False

        if metadata is None:
            logger.warning("Kafka вернула пустые метаданные кластера")
            return False

        topic_metadata = metadata.topics.get(
            self._topic,
        )
        if topic_metadata is None:
            return False

        if topic_metadata.error is not None:
            logger.warning(
                "Kafka topic недоступен, topic=%s error=%s",
                self._topic,
                topic_metadata.error,
            )
            return False

        return True

    def close(self) -> None:
        """Остановить poller и дождаться отправки оставшихся сообщений."""
        if self._closed:
            return

        self._closed = True
        self._stop_event.set()

        self._poller.join(
            timeout=1,
        )

        remaining_messages = self._producer.flush(
            self._settings.kafka_flush_timeout_seconds,
        )

        if remaining_messages:
            logger.warning(
                "Kafka Producer завершён с недоставленными "
                "сообщениями: count=%s",
                remaining_messages,
            )

    def _poll_loop(self) -> None:
        """Периодически обрабатывать callback-события Kafka Producer."""
        while not self._stop_event.is_set():
            try:
                self._producer.poll(0)
            except KafkaException as exc:
                logger.exception(
                    "Ошибка во время Kafka Producer poll: %s",
                    exc,
                )

            self._stop_event.wait(
                timeout=self._settings.kafka_poll_interval_seconds,
            )
