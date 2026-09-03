"""Оркестрация ETL-процесса Kafka → ClickHouse."""

import logging
from datetime import datetime, timezone
from threading import Event

from clickhouse.base import EventStorage
from clickhouse.exceptions import ClickHouseInsertError
from core.config import Settings
from kafka.base import (
    DeadLetterPublisher,
    EventConsumer,
    RejectedMessage,
)
from kafka.exceptions import (
    KafkaCommitError,
    KafkaConsumeError,
    KafkaDeadLetterPublishError,
)
from monitoring.metrics import (
    BATCH_PROCESSING_SECONDS,
    BATCHES_PROCESSED_TOTAL,
    CLICKHOUSE_RETRIES_TOTAL,
    CURRENT_BATCH_SIZE,
    DLQ_EVENTS_PUBLISHED_TOTAL,
    DLQ_PUBLISH_ERRORS_TOTAL,
    EVENTS_PROCESSED_TOTAL,
    EVENTS_REJECTED_TOTAL,
    KAFKA_COMMIT_ERRORS_TOTAL,
    PROCESSING_ERRORS_TOTAL,
)
from services.exceptions import (
    ETLProcessingError,
    EventMappingError,
)
from services.mapper import EventMapper

logger = logging.getLogger(__name__)


class ETLService:
    """Управляет переносом событий из Kafka в ClickHouse."""

    def __init__(
        self,
        *,
        settings: Settings,
        consumer: EventConsumer,
        storage: EventStorage,
        mapper: EventMapper,
        dead_letter_publisher: DeadLetterPublisher,
    ) -> None:
        """Создать ETL-сервис."""
        self._settings = settings
        self._consumer = consumer
        self._storage = storage
        self._mapper = mapper
        self._dead_letter_publisher = dead_letter_publisher

    def run(
        self,
        stop_event: Event,
    ) -> None:
        """Запустить основной цикл ETL."""
        self._subscribe_with_retry(
            stop_event,
        )

        kafka_retry_delay = self._settings.kafka_retry_initial_delay_seconds

        logger.info("ETL-сервис запущен")

        while not stop_event.is_set():
            try:
                messages = self._consumer.poll_batch()

                kafka_retry_delay = (
                    self._settings.kafka_retry_initial_delay_seconds
                )
            except KafkaConsumeError:
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception("Ошибка чтения Kafka")

                if stop_event.wait(kafka_retry_delay):
                    break

                kafka_retry_delay = min(
                    kafka_retry_delay * 2,
                    self._settings.kafka_retry_max_delay_seconds,
                )
                continue

            if not messages:
                continue

            CURRENT_BATCH_SIZE.set(
                len(messages),
            )

            try:
                with BATCH_PROCESSING_SECONDS.time():
                    ingested_at = datetime.now(
                        timezone.utc,
                    )

                    rows = []
                    rejected_messages: list[RejectedMessage] = []

                    for message in messages:
                        try:
                            row = self._mapper.map_message(
                                message,
                                ingested_at=ingested_at,
                            )
                        except EventMappingError as exc:
                            rejected_messages.append(
                                RejectedMessage(
                                    message=message,
                                    error_type=(type(exc).__name__),
                                    error_message=str(exc),
                                )
                            )

                            logger.warning(
                                "Kafka-событие отклонено "
                                "и будет отправлено в DLQ: "
                                "topic=%s partition=%s "
                                "offset=%s error=%s",
                                message.topic,
                                message.partition,
                                message.offset,
                                exc,
                            )
                        else:
                            rows.append(row)

                    if rows:
                        inserted = self._insert_with_retry(
                            rows,
                            stop_event,
                        )

                        if not inserted:
                            break

                    if rejected_messages:
                        published = self._publish_dlq_with_retry(
                            rejected_messages,
                            stop_event,
                        )

                        if not published:
                            break

                    committed = self._commit_with_retry(
                        messages,
                        stop_event,
                    )

                    if not committed:
                        break

                EVENTS_PROCESSED_TOTAL.inc(
                    len(rows),
                )
                EVENTS_REJECTED_TOTAL.inc(
                    len(rejected_messages),
                )
                BATCHES_PROCESSED_TOTAL.inc()

                logger.info(
                    "Пакет событий полностью обработан: "
                    "messages=%s valid=%s rejected=%s",
                    len(messages),
                    len(rows),
                    len(rejected_messages),
                )
            finally:
                CURRENT_BATCH_SIZE.set(0)

        logger.info("Основной цикл ETL остановлен")

    def _subscribe_with_retry(
        self,
        stop_event: Event,
    ) -> None:
        """Подписаться на Kafka с повторными попытками."""
        delay = self._settings.kafka_retry_initial_delay_seconds

        while not stop_event.is_set():
            try:
                self._consumer.subscribe()
                return
            except KafkaConsumeError:
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception("Не удалось подписаться на Kafka")

                if stop_event.wait(delay):
                    return

                delay = min(
                    delay * 2,
                    self._settings.kafka_retry_max_delay_seconds,
                )

    def _insert_with_retry(
        self,
        rows,
        stop_event: Event,
    ) -> bool:
        """Записать пакет в ClickHouse с повторными попытками."""
        retry_count = 0

        delay = self._settings.clickhouse_retry_initial_delay_seconds

        while True:
            try:
                self._storage.insert_batch(
                    rows,
                )

                return True
            except ClickHouseInsertError as exc:
                retry_count += 1

                PROCESSING_ERRORS_TOTAL.inc()

                max_retries = self._settings.clickhouse_max_retries

                if max_retries > 0 and retry_count > max_retries:
                    raise ETLProcessingError(
                        "Исчерпаны повторные попытки записи в ClickHouse"
                    ) from exc

                CLICKHOUSE_RETRIES_TOTAL.inc()

                logger.warning(
                    "ClickHouse недоступен, "
                    "повторная попытка записи: "
                    "retry=%s delay=%s",
                    retry_count,
                    delay,
                )

                if stop_event.wait(delay):
                    return False

                delay = min(
                    delay * 2,
                    self._settings.clickhouse_retry_max_delay_seconds,
                )

    def _publish_dlq_with_retry(
        self,
        messages: list[RejectedMessage],
        stop_event: Event,
    ) -> bool:
        """Опубликовать rejected messages в DLQ с retry."""
        delay = self._settings.kafka_retry_initial_delay_seconds

        while True:
            try:
                self._dead_letter_publisher.publish_batch(
                    messages,
                )

                DLQ_EVENTS_PUBLISHED_TOTAL.inc(
                    len(messages),
                )

                return True
            except KafkaDeadLetterPublishError:
                PROCESSING_ERRORS_TOTAL.inc()
                DLQ_PUBLISH_ERRORS_TOTAL.inc()

                logger.exception(
                    "Не удалось опубликовать события в Kafka DLQ: "
                    "count=%s delay=%s",
                    len(messages),
                    delay,
                )

                if stop_event.wait(delay):
                    return False

                delay = min(
                    delay * 2,
                    self._settings.kafka_retry_max_delay_seconds,
                )

    def _commit_with_retry(
        self,
        messages,
        stop_event: Event,
    ) -> bool:
        """Подтвердить Kafka offsets с повторными попытками."""
        delay = self._settings.kafka_retry_initial_delay_seconds

        retry_count = 0

        while True:
            try:
                self._consumer.commit_offsets(
                    messages,
                )

                return True
            except KafkaCommitError:
                retry_count += 1

                KAFKA_COMMIT_ERRORS_TOTAL.inc()
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception(
                    "Не удалось подтвердить Kafka offsets: retry=%s delay=%s",
                    retry_count,
                    delay,
                )

                if stop_event.wait(delay):
                    return False

                delay = min(
                    delay * 2,
                    self._settings.kafka_retry_max_delay_seconds,
                )
