"""Настройка распределённой трассировки OpenTelemetry."""

import inspect
import os
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

CallableT = TypeVar(
    "CallableT",
    bound=Callable[..., Any],
)

_configured_provider: TracerProvider | None = None


def configure_tracing(
    default_service_name: str,
) -> TracerProvider | None:
    """Создаёт и регистрирует провайдер трассировки один раз."""
    global _configured_provider

    if _configured_provider is not None:
        return _configured_provider

    enabled = os.getenv(
        "OTEL_ENABLED",
        "false",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if not enabled:
        return None

    service_name = os.getenv(
        "OTEL_SERVICE_NAME",
        default_service_name,
    )
    endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://jaeger:4317",
    )
    insecure = os.getenv(
        "OTEL_EXPORTER_OTLP_INSECURE",
        "true",
    ).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    provider = TracerProvider(
        resource=Resource.create(
            {
                SERVICE_NAME: service_name,
            },
        ),
        sampler=ALWAYS_ON,
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=endpoint,
                insecure=insecure,
            ),
        ),
    )

    trace.set_tracer_provider(provider)
    _configured_provider = provider

    return provider


def shutdown_tracing() -> None:
    """Отправляет оствшиеся spans и завершает provider."""
    if _configured_provider is None:
        return

    _configured_provider.force_flush(
        timeout_millis=5000,
    )
    _configured_provider.shutdown()


def trace_method(span_name: str) -> Callable[[CallableT], CallableT]:
    """Оборачивает синхронный или асинхронный метод в дочерний span."""

    def decorator(func: CallableT) -> CallableT:
        tracer = trace.get_tracer(func.__module__)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                with tracer.start_as_current_span(span_name):
                    return await func(*args, **kwargs)

            return cast(CallableT, async_wrapper)

        @wraps(func)
        def sync_wrapper(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            with tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)

        return cast(CallableT, sync_wrapper)

    return decorator
