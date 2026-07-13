"""Создание body запросов для поиска персон."""
from typing import Any


def build_persons_body(
    query: str | None,
    sort: str | None,
    page_number: int,
    page_size: int,
    person_sort_fields: dict[str, str],
) -> dict[str, Any]:
    """Формирует запрос Elasticsearch для получения и поиска персон."""
    search_query: dict = {
        'match_all': {},
    }
    if query:
        search_query = {
            'match': {
                'full_name': query,
            },
        }

    body = {
        'query': search_query,
        'from': (page_number - 1) * page_size,
        'size': page_size,
    }

    if sort:
        order = 'desc' if sort.startswith('-') else 'asc'
        sort_field = person_sort_fields.get(
            sort.lstrip('-'),
            'full_name.raw',
        )

        body['sort'] = [
            {
                sort_field: {
                    'order': order,
                },
            },
        ]

    return body


def build_person_films_body(
    person_id: str,
    page_number: int,
    page_size: int,
) -> dict[str, Any]:
    """Формирует запрос Elasticsearch для получения фильмов персоны."""
    body = {
        '_source': ['uuid', 'title', 'imdb_rating'],
        'query': {
            'bool': {
                'should': [
                    {
                        'nested': {
                            'path': 'actors',
                            'query': {
                                'term': {
                                    'actors.uuid': person_id,
                                },
                            },
                        },
                    },
                    {
                        'nested': {
                            'path': 'writers',
                            'query': {
                                'term': {
                                    'writers.uuid': person_id,
                                },
                            },
                        },
                    },
                    {
                        'nested': {
                            'path': 'directors',
                            'query': {
                                'term': {
                                    'directors.uuid': person_id,
                                },
                            },
                        },
                    },
                ],
                'minimum_should_match': 1,
            },
        },
        'sort': [
            {
                'imdb_rating': {
                    'order': 'desc',
                },
            },
        ],
        'from': (page_number - 1) * page_size,
        'size': page_size,
    }

    return body
