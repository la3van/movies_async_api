"""Точка входа ETL-сервиса переноса пользовательских событий в ClickHouse."""

import logging
import signal
from logging.config import dictConfig
from threading import Event
from types import FrameType

from clickhouse.client import ClickHouseEventStorage
from clickhouse_connect.driver.exceptions import ClickHouseError
from core.config import Settings, get_settings
from core.logger import LOGGING_CONFIG
from kafka.consumer import KafkaBatchConsumer
from kafka.dlq import KafkaDeadLetterPublisher
from monitoring.metrics import start_metrics_server
from services.etl import ETLService
from services.exceptions import ETLProcessingError
from services.mapper import EventMapper

logger = logging.getLogger(__name__)


def register_signal_handlers(
    stop_event: Event,
) -> None:
    """Зарегистрировать обработчики сигналов завершения процесса."""

    def handle_shutdown_signal(
        signum: int,
        frame: FrameType | None,
    ) -> None:
        """Запросить корректное завершение ETL-процесса."""
        logger.info(
            "Получен сигнал завершения: signal=%s",
            signum,
        )

        stop_event.set()

    signal.signal(
        signal.SIGTERM,
        handle_shutdown_signal,
    )
    signal.signal(
        signal.SIGINT,
        handle_shutdown_signal,
    )


def create_clickhouse_storage(
    settings: Settings,
    stop_event: Event,
) -> ClickHouseEventStorage | None:
    """Создать клиент ClickHouse с повторными попытками при недоступности."""
    retry_count = 0

    delay = settings.clickhouse_retry_initial_delay_seconds

    while not stop_event.is_set():
        try:
            storage = ClickHouseEventStorage(
                settings=settings,
            )

            if not storage.is_ready():
                storage.close()
                raise ClickHouseError("ClickHouse недоступен")
        except ClickHouseError:
            retry_count += 1

            max_retries = settings.clickhouse_max_retries

            logger.exception(
                "Не удалось подключиться к ClickHouse: retry=%s delay=%s",
                retry_count,
                delay,
            )

            if max_retries > 0 and retry_count > max_retries:
                raise

            if stop_event.wait(delay):
                return None

            delay = min(
                delay * 2,
                settings.clickhouse_retry_max_delay_seconds,
            )
            continue

        logger.info("Подключение к ClickHouse установлено")

        return storage

    return None


def main() -> None:
    """Создать зависимости и запустить основной цикл ETL."""
    dictConfig(
        LOGGING_CONFIG,
    )

    settings = get_settings()
    stop_event = Event()

    register_signal_handlers(
        stop_event,
    )
    start_metrics_server(
        settings,
    )

    logger.info(
        "Сервер метрик запущен: host=%s port=%s",
        settings.metrics_host,
        settings.metrics_port,
    )

    logger.info(
        "Kafka offset policy: group_id=%s auto_offset_reset=%s",
        settings.kafka_group_id,
        settings.kafka_auto_offset_reset,
    )

    consumer = KafkaBatchConsumer(
        settings=settings,
    )
    dead_letter_publisher = KafkaDeadLetterPublisher(
        settings=settings,
    )
    storage = None

    try:
        storage = create_clickhouse_storage(
            settings=settings,
            stop_event=stop_event,
        )

        if storage is None:
            return

        mapper = EventMapper()

        etl_service = ETLService(
            settings=settings,
            consumer=consumer,
            storage=storage,
            mapper=mapper,
            dead_letter_publisher=(dead_letter_publisher),
        )

        etl_service.run(
            stop_event=stop_event,
        )
    except ETLProcessingError:
        logger.exception(
            "ETL-сервис остановлен из-за критической ошибки обработки данных"
        )
        raise
    except ClickHouseError:
        logger.exception(
            "ETL-сервис не смог установить соединение с ClickHouse"
        )
        raise
    finally:
        logger.info("Начато завершение ETL-сервиса")

        consumer.close()
        dead_letter_publisher.close()

        if storage is not None:
            storage.close()

        logger.info("ETL-сервис завершён")


if __name__ == "__main__":
    main()
