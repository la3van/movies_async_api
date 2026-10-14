"""Optional observability with strict scrubbing of request and local data."""

import os
from typing import Any

import sentry_sdk
from sentry_sdk.types import Event, Hint


def scrub_event(event: Event, hint: Hint) -> Event:
    del hint
    event.pop("request", None)
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    event.pop("extra", None)
    event.pop("contexts", None)
    for item in event.get("exception", {}).get("values", []):
        item["value"] = "redacted"
        for frame in item.get("stacktrace", {}).get("frames", []):
            frame.pop("vars", None)
    return event


def initialize() -> Any:
    if os.getenv("SENTRY_DSN"):
        sentry_sdk.init(
            dsn=os.environ["SENTRY_DSN"],
            send_default_pii=False,
            include_local_variables=False,
            max_request_body_size="never",
            before_send=scrub_event,
            traces_sample_rate=0,
        )
    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return None
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(
        resource=Resource.create({"service.name": "profile-service"})
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=os.getenv(
                    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"
                ),
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(provider)
    return provider
