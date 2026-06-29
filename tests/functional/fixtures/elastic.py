"""Общие фикстуры Elasticsearch."""
from typing import Any

import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from tests.functional.settings import test_settings
from tests.functional.utils.helpers import (
    build_bulk_actions,
    recreate_index,
)


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
