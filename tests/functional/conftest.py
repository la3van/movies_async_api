"""Общие фикстуры функциональных тестов."""
import aiohttp
import asyncio
import pytest
import pytest_asyncio

from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from redis.asyncio import Redis

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import (
    build_bulk_actions,
    recreate_index,
)

pytest_plugins = [
    'tests.functional.testdata.documents',
]


@pytest.fixture(scope='session')
def event_loop():
    """Создаёт event loop на время тестовой сессии."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(name='es_write_data')
def es_write_data(es_client: AsyncElasticsearch):
    """Возвращает функцию пересоздания индекса и загрузки документов."""
    async def inner(
        index: str,
        index_schema: dict[str, Any],
        documents: list[dict[str, Any]],
    ) -> None:
        """Пересоздаёт индекс и загружает в него переданные документы."""
        await recreate_index(
            es_client=es_client,
            index=index,
            index_schema=index_schema,
        )

        actions = build_bulk_actions(
            index=index,
            documents=documents,
        )

        _, errors = await async_bulk(
            client=es_client,
            actions=actions,
            refresh='wait_for',
            raise_on_error=False,
        )

        if errors:
            raise Exception('Ошибка записи данных в Elasticsearch')

    return inner


@pytest_asyncio.fixture(name='movies_in_es')
async def movies_in_es(
    movie_documents: dict[str, Any],
    es_write_data,
):
    """Загружает тестовые фильмы в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=movie_documents,
    )

    return movie_documents


@pytest_asyncio.fixture(name='isolated_movie_in_es')
async def isolated_movie_in_es(
    movies_in_es,
    isolated_movie_document: dict[str, Any],
    es_write_data,
):
    """Загружает изолированный фильм для проверки отсутствия похожих."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=[isolated_movie_document],
    )

    return isolated_movie_document


@pytest_asyncio.fixture(name='movie_without_relations_in_es')
async def movie_without_relations_in_es(
    movies_in_es,
    movie_without_relations_document: dict[str, Any],
    es_write_data,
):
    """Загружает фильм без жанров и связанных персон."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=[movie_without_relations_document],
    )

    return movie_without_relations_document


@pytest_asyncio.fixture(name='genres_in_es')
async def genres_in_es(
    genre_documents: list[dict[str, Any]],
    es_write_data,
):
    """Загружает тестовые жанры в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_genres_index,
        index_schema=test_settings.es_genres_index_schema,
        documents=genre_documents,
    )

    return genre_documents


@pytest_asyncio.fixture(name='persons_in_es')
async def persons_in_es(
    person_documents: list[dict[str, Any]],
    es_write_data,
):
    """Загружает тестовых персон в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_persons_index,
        index_schema=test_settings.es_persons_index_schema,
        documents=person_documents,
    )

    return person_documents


@pytest_asyncio.fixture(name='es_client', scope='session')
async def es_client():
    """Создаёт Elasticsearch-клиент на время тестовой сессии."""
    es_client = AsyncElasticsearch(
        hosts=[test_settings.get_elastic_url()],
        verify_certs=False,
    )
    yield es_client
    await es_client.close()


@pytest_asyncio.fixture(name='es_delete_document')
async def es_delete_document(
    es_client: AsyncElasticsearch,
):
    """Возвращает функцию удаления документа из Elasticsearch."""
    async def inner(
        index: str,
        document_id: str,
    ) -> None:
        """Функция удаления документа из Elasticsearch."""
        await es_client.delete(
            index=index,
            id=document_id,
            refresh='wait_for',
        )

    return inner


@pytest_asyncio.fixture(name='redis_client', scope='session')
async def redis_client():
    """Создаёт Redis-клиент на время тестовой сессии."""
    redis_client = Redis.from_url(
        test_settings.get_redis_url(),
        socket_connect_timeout=(
            test_settings.redis_socket_connect_timeout
        ),
        socket_timeout=test_settings.redis_socket_timeout,
    )
    yield redis_client
    await redis_client.aclose()


@pytest_asyncio.fixture(name='redis_clear', autouse=True)
async def redis_clear(redis_client):
    """Очищает Redis до и после каждого теста."""
    await redis_client.flushdb()

    yield

    await redis_client.flushdb()


@pytest_asyncio.fixture(name='http_session', scope='session')
async def http_session():
    """Создаёт HTTP-сессию на время тестовой сессии."""
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture(name='make_get_request')
def make_get_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения GET-запросов к тестируемому API."""
    async def inner(
        url: str,
        query_data: dict[str, Any] | None = None
    ):
        """Выполняет GET-запрос с переданными query-параметрами."""
        url = (
            f'{test_settings.service_url.rstrip("/")}/'
            f'{url.lstrip("/")}'
        )

        return await http_session.get(
            url,
            params=query_data,
        )

    return inner
