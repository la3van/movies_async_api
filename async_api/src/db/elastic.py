"""Модуль зависимостей относительно Elasticsearch'а."""
from typing import Optional

from elasticsearch import AsyncElasticsearch

from core.config import get_settings

elastic: Optional[AsyncElasticsearch] = None


async def init_elastic() -> None:
    """Инициализирует клиент Elasticsearch."""
    global elastic

    settings = get_settings()

    elastic = AsyncElasticsearch(
        hosts=[settings.elastic_url],
        request_timeout=settings.elastic_request_timeout,
    )


async def close_elastic() -> None:
    """Закрывает соединение с Elasticsearch."""
    global elastic

    if elastic is not None:
        await elastic.close()
        elastic = None


async def get_elastic() -> AsyncElasticsearch:
    """Возвращает клиент Elasticsearch для dependency injection."""
    if elastic is None:
        raise RuntimeError('Elasticsearch client is not initialized')

    return elastic
