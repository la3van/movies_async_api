"""Настройка распределённой трассировки OpenTelemetry."""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.resources import (
    Resource,
    SERVICE_NAME,
)
from opentelemetry.sdk.trace import (
    TracerProvider,
)
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
)

from core.config import Settings

_tracer_provider: TracerProvider | None = None


def configure_tracing(
    settings: Settings,
) -> TracerProvider | None:
    """Настроить распределённую трассировку приложения."""
    global _tracer_provider

    if not settings.otel_enabled:
        return None

    if _tracer_provider is not None:
        return _tracer_provider

    resource = Resource.create(
        {
            SERVICE_NAME: (
                settings.otel_service_name
            ),
        },
    )

    provider = TracerProvider(
        resource=resource,
    )

    exporter = OTLPSpanExporter(
        endpoint=(
            settings
            .otel_exporter_otlp_endpoint
        ),
        insecure=(
            settings
            .otel_exporter_otlp_insecure
        ),
    )

    processor = BatchSpanProcessor(
        exporter,
    )

    provider.add_span_processor(
        processor,
    )

    trace.set_tracer_provider(
        provider,
    )

    _tracer_provider = provider

    return provider


def shutdown_tracing() -> None:
    """Завершить трассировку и отправить накопленные спаны."""
    if _tracer_provider is None:
        return

    _tracer_provider.force_flush(
        timeout_millis=5_000,
    )

    _tracer_provider.shutdown()
