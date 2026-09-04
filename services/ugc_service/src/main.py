"""Точка входа FastAPI-приложения UGC Service."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from logging.config import dictConfig

from api.exception_handlers import register_exception_handlers
from api.health import router as health_router
from api.v1.router import api_router
from auth.client import close_auth_client, init_auth_client
from core.config import get_settings
from core.logger import LOGGING
from core.request_id import RequestIdMiddleware
from core.request_size import RequestSizeLimitMiddleware
from core.sentry import init_sentry
from core.tracing import configure_tracing, shutdown_tracing
from db.mongo import close_mongo, init_mongo
from db.redis import close_redis, init_redis
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from integrations.content import close_content_client, init_content_client
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from sentry_sdk.integrations.fastapi import FastApiIntegration

dictConfig(LOGGING)
settings = get_settings()

init_sentry(
    service_name=settings.project_name,
    integration=FastApiIntegration(
        transaction_style="endpoint",
    ),
)

tracer_provider = configure_tracing(default_service_name="ugc-service")
if tracer_provider is not None:
    PymongoInstrumentor().instrument(tracer_provider=tracer_provider)
    RedisInstrumentor().instrument(tracer_provider=tracer_provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Открыть и гарантированно закрыть внешние ресурсы приложения."""
    await init_mongo()
    await init_redis()
    await init_auth_client()
    await init_content_client()
    try:
        yield
    finally:
        await close_content_client()
        await close_auth_client()
        await close_redis()
        await close_mongo()
        shutdown_tracing()


app = FastAPI(
    title=settings.project_name,
    description=(
        "CRUD API пользовательских закладок, оценок, рецензий и голосов "
        "за рецензии с хранением в MongoDB."
    ),
    version=settings.api_version,
    docs_url="/ugc/docs",
    openapi_url="/ugc/openapi.json",
    redoc_url="/ugc/redoc",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_bytes=settings.max_request_body_bytes,
)
app.add_middleware(RequestIdMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.include_router(health_router)

if tracer_provider is not None:
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls="health,ready",
    )
