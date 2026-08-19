"""Метрики состояния и производительности ETL-сервиса."""
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

from core.config import Settings


EVENTS_PROCESSED_TOTAL = Counter(
    "events_etl_processed_total",
    "Общее количество успешно обработанных пользовательских событий.",
)

BATCHES_PROCESSED_TOTAL = Counter(
    "events_etl_batches_processed_total",
    "Общее количество успешно обработанных пакетов событий.",
)

PROCESSING_ERRORS_TOTAL = Counter(
    "events_etl_processing_errors_total",
    "Общее количество ошибок обработки пакетов событий.",
)

CLICKHOUSE_RETRIES_TOTAL = Counter(
    "events_etl_clickhouse_retries_total",
    "Общее количество повторных попыток записи в ClickHouse.",
)

KAFKA_COMMIT_ERRORS_TOTAL = Counter(
    "events_etl_kafka_commit_errors_total",
    "Общее количество ошибок подтверждения Kafka offsets.",
)

CURRENT_BATCH_SIZE = Gauge(
    "events_etl_current_batch_size",
    "Количество событий в текущем пакете.",
)

BATCH_PROCESSING_SECONDS = Histogram(
    "events_etl_batch_processing_seconds",
    "Время полной обработки одного пакета событий.",
)


def start_metrics_server(
    settings: Settings,
) -> None:
    """Запустить HTTP-сервер экспорта Prometheus-метрик."""
    start_http_server(
        port=settings.metrics_port,
        addr=settings.metrics_host,
    )
