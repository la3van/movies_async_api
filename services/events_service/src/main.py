"""Создание и конфигурация Flask-приложения сбора событий."""
import atexit
from logging.config import dictConfig

from flask import Flask
from opentelemetry.instrumentation.flask import FlaskInstrumentor

from api.exception_handlers import register_exception_handlers
from api.health import router as health_router
from api.v1.router import api_router
from core.config import Settings, get_settings
from core.logger import LOGGING_CONFIG
from core.request_id import register_request_id
from core.tracing import configure_tracing, shutdown_tracing
from kafka.base import EventPublisher
from kafka.producer import KafkaEventPublisher
from services.events import EventService

dictConfig(LOGGING_CONFIG)


def create_app(
    settings: Settings | None = None,
    publisher: EventPublisher | None = None,
) -> Flask:
    """Создать и настроить Flask-приложение."""
    settings = settings or get_settings()

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = (
        settings.max_event_request_bytes
    )

    tracer_provider = configure_tracing(
        settings,
    )

    owns_publisher = publisher is None
    if publisher is None:
        publisher = KafkaEventPublisher(
            settings=settings,
            tracer_provider=tracer_provider,
        )

    event_service = EventService(
        publisher=publisher,
    )

    app.extensions["event_service"] = event_service

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

    if tracer_provider is not None:
        atexit.register(
            shutdown_tracing,
        )

    return app


app = create_app()
