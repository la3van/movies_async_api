"""Модуль зависимостей относительно Elasticsearch'а."""

from core.config import get_settings
from elasticsearch import AsyncElasticsearch

elastic: AsyncElasticsearch | None = None


async def init_elastic() -> None:
    """Инициализирует клиент Elasticsearch."""
    global elastic

    settings = get_settings()

    elastic = AsyncElasticsearch(
        hosts=[settings.elastic_url],
        request_timeout=settings.elastic_request_timeout,
        max_retries=settings.elastic_max_retries,
        retry_on_timeout=settings.elastic_retry_on_timeout,
        retry_on_status=settings.elastic_retry_on_status,
        retry_backoff_base=settings.elastic_retry_backoff_base,
        retry_backoff_cap=settings.elastic_retry_backoff_cap,
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
        raise RuntimeError("Elasticsearch client is not initialized")

    return elastic
