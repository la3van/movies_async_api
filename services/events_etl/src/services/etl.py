"""Оркестрация ETL-процесса Kafka → ClickHouse."""
import logging
from threading import Event

from clickhouse.base import EventStorage
from clickhouse.exceptions import ClickHouseInsertError
from core.config import Settings
from kafka.base import EventConsumer
from kafka.exceptions import (
    KafkaCommitError,
    KafkaConsumeError,
)
from monitoring.metrics import (
    BATCHES_PROCESSED_TOTAL,
    BATCH_PROCESSING_SECONDS,
    CLICKHOUSE_RETRIES_TOTAL,
    CURRENT_BATCH_SIZE,
    EVENTS_PROCESSED_TOTAL,
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
    ) -> None:
        """Создать ETL-сервис."""
        self._settings = settings
        self._consumer = consumer
        self._storage = storage
        self._mapper = mapper

    def run(
        self,
        stop_event: Event,
    ) -> None:
        """Запустить основной цикл ETL."""
        self._subscribe_with_retry(
            stop_event,
        )

        kafka_retry_delay = (
            self._settings
            .kafka_retry_initial_delay_seconds
        )

        logger.info(
            "ETL-сервис запущен"
        )

        while not stop_event.is_set():
            try:
                messages = (
                    self._consumer.poll_batch()
                )

                kafka_retry_delay = (
                    self._settings
                    .kafka_retry_initial_delay_seconds
                )
            except KafkaConsumeError:
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception(
                    "Ошибка чтения Kafka"
                )

                if stop_event.wait(
                    kafka_retry_delay
                ):
                    break

                kafka_retry_delay = min(
                    kafka_retry_delay * 2,
                    self._settings
                    .kafka_retry_max_delay_seconds,
                )
                continue

            if not messages:
                continue

            CURRENT_BATCH_SIZE.set(
                len(messages),
            )

            try:
                with BATCH_PROCESSING_SECONDS.time():
                    rows = self._mapper.map_batch(
                        messages,
                    )

                    inserted = (
                        self._insert_with_retry(
                            rows,
                            stop_event,
                        )
                    )

                    if not inserted:
                        break

                    committed = (
                        self._commit_with_retry(
                            messages,
                            stop_event,
                        )
                    )

                    if not committed:
                        break

                EVENTS_PROCESSED_TOTAL.inc(
                    len(messages),
                )

                BATCHES_PROCESSED_TOTAL.inc()

                logger.info(
                    "Пакет событий полностью обработан: "
                    "messages=%s",
                    len(messages),
                )
            except EventMappingError as exc:
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception(
                    "Не удалось преобразовать "
                    "Kafka-событие"
                )

                raise ETLProcessingError(
                    "Обнаружено некорректное "
                    "пользовательское событие"
                ) from exc
            finally:
                CURRENT_BATCH_SIZE.set(0)

        logger.info(
            "Основной цикл ETL остановлен"
        )

    def _subscribe_with_retry(
        self,
        stop_event: Event,
    ) -> None:
        """Подписаться на Kafka с повторными попытками."""
        delay = (
            self._settings
            .kafka_retry_initial_delay_seconds
        )

        while not stop_event.is_set():
            try:
                self._consumer.subscribe()
                return
            except KafkaConsumeError:
                PROCESSING_ERRORS_TOTAL.inc()

                logger.exception(
                    "Не удалось подписаться на Kafka"
                )

                if stop_event.wait(delay):
                    return

                delay = min(
                    delay * 2,
                    self._settings
                    .kafka_retry_max_delay_seconds,
                )

    def _insert_with_retry(
        self,
        rows,
        stop_event: Event,
    ) -> bool:
        """Записать пакет в ClickHouse с повторными попытками."""
        retry_count = 0

        delay = (
            self._settings
            .clickhouse_retry_initial_delay_seconds
        )

        while True:
            try:
                self._storage.insert_batch(
                    rows,
                )

                return True
            except ClickHouseInsertError as exc:
                retry_count += 1

                PROCESSING_ERRORS_TOTAL.inc()

                max_retries = (
                    self._settings
                    .clickhouse_max_retries
                )

                if (
                    max_retries > 0
                    and retry_count > max_retries
                ):
                    raise ETLProcessingError(
                        "Исчерпаны повторные попытки "
                        "записи в ClickHouse"
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
                    self._settings
                    .clickhouse_retry_max_delay_seconds,
                )

    def _commit_with_retry(
        self,
        messages,
        stop_event: Event,
    ) -> bool:
        """Подтвердить Kafka offsets с повторными попытками."""
        delay = (
            self._settings
            .kafka_retry_initial_delay_seconds
        )

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
                    "Не удалось подтвердить "
                    "Kafka offsets: "
                    "retry=%s delay=%s",
                    retry_count,
                    delay,
                )

                if stop_event.wait(delay):
                    return False

                delay = min(
                    delay * 2,
                    self._settings
                    .kafka_retry_max_delay_seconds,
                )
