"""JSON-логи, метрики, Sentry и передача контекста трассировки."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import sentry_sdk
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter

from core.config import Settings

OPERATIONS = Counter(
    "notification_operations_total", "Operations", ["kind", "outcome"]
)


DELIVERY_ERRORS = Counter(
    "notification_delivery_errors_total",
    "Delivery errors by safe reason code",
    ["error_code"],
)


class JsonFormatter(logging.Formatter):
    """Форматировщик логов без сериализации данных исключения."""

    def format(self, record: logging.LogRecord) -> str:
        # Не сериализуем исключение с SQL-параметрами или текстом письма.
        """Сериализует уровень, источник и безопасное сообщение лога."""
        return json.dumps(
            {
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


class SentryHandler(logging.Handler):
    """Отправка статических сообщений об ошибках в Sentry."""

    def emit(self, record: logging.LogRecord) -> None:
        # Передаём только статическое сообщение приложения, без exc_info.
        """Передаёт в Sentry ошибки приложения без исходного исключения."""
        if record.levelno >= logging.ERROR and record.name.startswith(
            ("messaging", "core")
        ):
            sentry_sdk.capture_message(record.getMessage(), level="error")


def configure(settings: Settings) -> None:
    """Настраивает вывод логов и включённые средства наблюдаемости."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            send_default_pii=False,
            default_integrations=False,
        )
        logging.getLogger().addHandler(SentryHandler())
    if settings.otel_endpoint:
        provider = TracerProvider(
            resource=Resource.create(
                {
                    "service.name": settings.service_name,
                }
            )
        )
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=settings.otel_endpoint,
                    insecure=True,
                )
            )
        )
        trace.set_tracer_provider(provider)


@contextmanager
def span(name: str, carrier: dict[str, str] | None = None) -> Iterator[None]:
    """Создаёт span с родительским контекстом без записи исключений."""
    with trace.get_tracer("notifications").start_as_current_span(
        name,
        context=extract(carrier or {}),
        record_exception=False,
        set_status_on_exception=False,
    ):
        yield


def carrier() -> dict[str, str]:
    """Возвращает текущий контекст для передачи в сообщение."""
    result: dict[str, str] = {}
    inject(result)
    return result


def shutdown() -> None:
    """Завершает экспорт накопленной телеметрии."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.shutdown()
    sentry_sdk.flush(timeout=2)
