"""Фикстуры загрузки фильмов в Elasticsearch."""

from typing import Any

import pytest_asyncio

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name="movies_in_es")
async def movies_in_es(
    movie_documents: dict[str, Any],
    es_write_data,
) -> list[dict[str, Any]]:
    """Загружает тестовые фильмы в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=movie_documents,
    )

    return movie_documents


@pytest_asyncio.fixture(name="movies_with_isolated_movie_in_es")
async def movies_with_isolated_movie_in_es(
    movie_documents: list[dict[str, Any]],
    isolated_movie_document: dict[str, Any],
    es_write_data,
) -> dict[str, Any]:
    """Загружает фильмы для проверки fallback-поиска по жанрам."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=movie_documents + [isolated_movie_document],
    )

    return isolated_movie_document


@pytest_asyncio.fixture(name="movies_without_matches_in_es")
async def movies_without_matches_in_es(
    movies_without_matches_documents: list[dict[str, Any]],
    es_write_data,
) -> list[dict[str, Any]]:
    """Загружает фильм и неподходящих кандидатов в Elasticsearch."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=movies_without_matches_documents,
    )

    return movies_without_matches_documents


@pytest_asyncio.fixture(name="movie_without_relations_in_es")
async def movie_without_relations_in_es(
    movie_without_relations_document: dict[str, Any],
    es_write_data,
) -> dict[str, Any]:
    """Загружает фильм без жанров и связанных персон."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=[movie_without_relations_document],
    )

    return movie_without_relations_document


@pytest_asyncio.fixture(name="similar_movies_in_es")
async def similar_movies_in_es(
    similar_movies_documents: list[dict[str, Any]],
    es_write_data,
) -> list[dict[str, Any]]:
    """Загружает фильмы для проверки more_like_this."""
    await es_write_data(
        index=test_settings.es_movies_index,
        index_schema=test_settings.es_movies_index_schema,
        documents=similar_movies_documents,
    )

    return similar_movies_documents
