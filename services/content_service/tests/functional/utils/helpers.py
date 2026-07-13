"""Вспомогательные функции функциональных тестов."""
from collections.abc import Callable, Iterable
from typing import Any

from elasticsearch import AsyncElasticsearch

from typing import Literal

ExpectedSearchCase = Literal[
    'title',
    'description',
    'person',
    'not_found',
]


def build_bulk_actions(
    index: str,
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Формирует bulk-операции для загрузки документов в Elasticsearch."""
    return [
        {
            '_index': index,
            '_id': document['uuid'],
            '_source': document,
        }
        for document in documents
    ]


async def recreate_index(
    es_client: AsyncElasticsearch,
    index: str,
    index_schema: dict[str, Any],
) -> None:
    """Пересоздаёт Elasticsearch-индекс по переданной схеме."""
    if await es_client.indices.exists(
        index=index
    ):
        await es_client.indices.delete(
            index=index
        )

    await es_client.indices.create(
        index=index,
        **index_schema,
    )


def build_expected_page(
    documents: list[dict[str, Any]],
    expected_indexes: Iterable[int],
    *,
    sort_field: str | None = None,
    reverse: bool | None = None,
    page_number: int,
    page_size: int,
    response_builder: Callable[
        [dict[str, Any]],
        dict[str, Any],
    ] | None = None,
) -> list[dict[str, Any]]:
    """Формирует ожидаемую страницу документов для проверки ответа."""
    expected_documents = [
        documents[index]
        for index in expected_indexes
    ]

    if sort_field:
        expected_documents = sorted(
            expected_documents,
            key=lambda document: document[sort_field],
            reverse=reverse,
        )

    start = (page_number - 1) * page_size
    end = start + page_size

    page = expected_documents[start:end]
    if response_builder is None:
        return page

    return [
        response_builder(document)
        for document in page
    ]


def build_expected_searched_movies(
    movies: list[dict[str, Any]],
    expected_case: ExpectedSearchCase,
) -> list[dict[str, Any]]:
    """Формирует ожидаемый результат поиска фильмов."""
    if expected_case == 'title':
        return [
            movie
            for movie in movies
            if 'Space' in movie['title']
        ]

    if expected_case == 'description':
        return [
            movie
            for movie in movies
            if 'Detective' in movie['description']
        ]

    if expected_case == 'person':
        return [
            movie
            for movie in movies
            if any(
                'Jason' in person['full_name']
                for role in (
                    'actors',
                    'writers',
                    'directors',
                )
                for person in movie[role]
            )
        ]

    if expected_case == 'not_found':
        return []

    raise ValueError(
        f'Unknown expected search case: {expected_case}',
    )
