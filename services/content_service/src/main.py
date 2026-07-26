"""Точка входа FastAPI-приложения."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from logging.config import dictConfig

from api.v1.router import api_router
from core.config import get_settings
from core.logger import LOGGING
from core.request_id import RequestIdMiddleware
from db.elastic import close_elastic, init_elastic
from db.redis import close_redis, init_redis
from auth.client import (
    close_auth_client,
    init_auth_client,
)

from opentelemetry.instrumentation.elasticsearch import (
    ElasticsearchInstrumentor,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from core.tracing import configure_tracing, shutdown_tracing

from opentelemetry.instrumentation.httpx import (
    HTTPXClientInstrumentor,
)

dictConfig(LOGGING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Упарвляет жизненным циклом приложения."""
    await init_elastic()
    await init_redis()
    await init_auth_client()

    try:
        yield
    finally:
        await close_elastic()
        await close_redis()
        await close_auth_client()
        shutdown_tracing()


settings = get_settings()

tracer_provider = configure_tracing(
    default_service_name="content-service",
)

if tracer_provider is not None:
    RedisInstrumentor().instrument(
        tracer_provider=tracer_provider,
    )
    ElasticsearchInstrumentor().instrument(
        tracer_provider=tracer_provider,
    )
    HTTPXClientInstrumentor().instrument(
        tracer_provider=tracer_provider,
    )

app = FastAPI(
    title=settings.project_name,
    description=(
        'Информация о фильмах, жанрах и людях,'
        'участвовавших в создании произведения'
    ),
    version='1.0.0',
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

if tracer_provider is not None:
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
    )
app.add_middleware(RequestIdMiddleware)

app.include_router(
    api_router,
    prefix='/api/v1',
)
