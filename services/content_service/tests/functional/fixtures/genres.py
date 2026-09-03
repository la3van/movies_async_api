"""Фикстуры загрузки жанров в Elasticsearch."""

from typing import Any

import pytest_asyncio

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name="genres_in_es")
async def genres_in_es(
    genre_documents: list[dict[str, Any]],
    es_write_data,
) -> list[dict[str, Any]]:
    """Загружает тестовые жанры в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_genres_index,
        index_schema=test_settings.es_genres_index_schema,
        documents=genre_documents,
    )

    return genre_documents
