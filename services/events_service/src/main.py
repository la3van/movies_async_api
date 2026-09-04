"""Создание и конфигурация Flask-приложения сбора событий."""

import atexit
from logging.config import dictConfig

import httpx
from api.exception_handlers import register_exception_handlers
from api.health import router as health_router
from api.v1.router import api_router
from auth.client import AuthServiceClient
from core.config import Settings, get_settings
from core.event_rate_limit import (
    EventRateLimiter,
    RedisEventRateLimiter,
)
from core.logger import LOGGING_CONFIG
from core.request_id import register_request_id
from core.sentry import init_sentry
from core.tracing import configure_tracing, shutdown_tracing
from flask import Flask
from kafka.base import EventPublisher
from kafka.producer import KafkaEventPublisher
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from redis import Redis
from sentry_sdk.integrations.flask import FlaskIntegration
from services.events import EventService

dictConfig(LOGGING_CONFIG)


def create_app(
    settings: Settings | None = None,
    publisher: EventPublisher | None = None,
    auth_client: AuthServiceClient | None = None,
    rate_limiter: EventRateLimiter | None = None,
) -> Flask:
    """Создать и настроить Flask-приложение."""
    settings = settings or get_settings()

    init_sentry(
        service_name=settings.project_name,
        integration=FlaskIntegration(
            transaction_style="endpoint",
        ),
    )

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = settings.max_event_request_bytes

    tracer_provider = configure_tracing(
        settings,
    )

    owns_publisher = publisher is None
    if publisher is None:
        publisher = KafkaEventPublisher(
            settings=settings,
            tracer_provider=tracer_provider,
        )

    owns_auth_client = auth_client is None
    if auth_client is None:
        auth_http_client = httpx.Client(
            base_url=settings.auth_service_base_url,
            timeout=httpx.Timeout(
                connect=(settings.auth_service_connect_timeout_seconds),
                read=(settings.auth_service_read_timeout_seconds),
                write=(settings.auth_service_read_timeout_seconds),
                pool=(settings.auth_service_connect_timeout_seconds),
            ),
            follow_redirects=False,
        )
        auth_client = AuthServiceClient(
            client=auth_http_client,
        )

    owns_rate_limiter = rate_limiter is None
    if rate_limiter is None:
        redis_client = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            socket_connect_timeout=(settings.redis_connect_timeout_seconds),
            socket_timeout=(settings.redis_socket_timeout_seconds),
        )
        rate_limiter = RedisEventRateLimiter(
            redis=redis_client,
            enabled=settings.event_rate_limit_enabled,
            key_prefix=settings.event_rate_limit_key_prefix,
            requests=settings.event_rate_limit_requests,
            window_seconds=(settings.event_rate_limit_window_seconds),
        )

    event_service = EventService(
        publisher=publisher,
    )

    app.extensions["event_service"] = event_service
    app.extensions["auth_client"] = auth_client
    app.extensions["event_rate_limiter"] = rate_limiter

    register_request_id(app)
    register_exception_handlers(app)

    app.register_blueprint(api_router)
    app.register_blueprint(health_router)

    if tracer_provider is not None:
        FlaskInstrumentor.instrument_app(
            app,
            tracer_provider=tracer_provider,
            excluded_urls="health,ready",
        )

    if owns_publisher:
        atexit.register(
            publisher.close,
        )
    if owns_auth_client:
        atexit.register(
            auth_client.close,
        )
    if owns_rate_limiter:
        atexit.register(
            rate_limiter.close,
        )

    if tracer_provider is not None:
        atexit.register(
            shutdown_tracing,
        )

    return app


app = create_app()
