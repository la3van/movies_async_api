"""Точка входа FastAPI-приложения auth-сервиса."""
from contextlib import asynccontextmanager
from logging.config import dictConfig
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from api.v1.router import api_router
from core.config import get_settings
from core.logger import LOGGING
from db.postgres import close_postgres, init_postgres
from db.redis import close_redis, init_redis

dictConfig(LOGGING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Управляет жизненным циклом приложения."""
    await init_postgres()
    await init_redis()

    yield

    await close_redis()
    await close_postgres()


settings = get_settings()

app = FastAPI(
    title=settings.project_name,
    description='Сервис аутентификации и авторизации для онлайн-кинотеатра',
    version='1.0.0',
    docs_url='/docs',
    openapi_url='/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(api_router, prefix='/api/v1')


@app.get('/health', tags=['health'])
async def health_check() -> dict[str, str]:
    """Проверяет, что auth-сервис запущен."""
    return {'status': 'ok'}
