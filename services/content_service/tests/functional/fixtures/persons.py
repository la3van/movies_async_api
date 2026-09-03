"""Фикстуры загрузки персон в Elasticsearch."""

from typing import Any

import pytest_asyncio

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name="persons_in_es")
async def persons_in_es(
    person_documents: list[dict[str, Any]],
    es_write_data,
) -> list[dict[str, Any]]:
    """Загружает тестовых персон в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_persons_index,
        index_schema=test_settings.es_persons_index_schema,
        documents=person_documents,
    )

    return person_documents
