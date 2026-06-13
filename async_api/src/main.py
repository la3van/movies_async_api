"""Точка входа FastAPI-приложения."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1.router import api_router
from core.config import get_settings
from db.elastic import close_elastic, init_elastic
from db.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Упарвляет жизненным циклом приложения."""
    await init_elastic()
    await init_redis()

    yield

    await close_elastic()
    await close_redis()


settings = get_settings()

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

app.include_router(
    api_router,
    prefix='/api/v1',
)
