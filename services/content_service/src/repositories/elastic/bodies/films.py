"""Создание body запросов для поиска фильмов."""

from typing import Any


def build_sorted_films_body(
    sort: str,
    genre_filter: str | None,
    page_number: int,
    page_size: int,
    film_sort_fields: dict[str, str],
) -> dict[str, Any]:
    """Формирует запрос Elasticsearch для сортировки и фильтрации фильмов."""
    order = "desc" if sort.startswith("-") else "asc"
    sort_field = film_sort_fields.get(
        sort.lstrip("-"),
        "imdb_rating",
    )

    search_query: dict[str, Any] = {
        "match_all": {},
    }

    if genre_filter:
        search_query = {
            "bool": {
                "filter": [
                    {
                        "nested": {
                            "path": "genre",
                            "query": {
                                "term": {
                                    "genre.uuid": genre_filter,
                                },
                            },
                        },
                    },
                ],
            },
        }

    return {
        "_source": ["uuid", "title", "imdb_rating"],
        "query": search_query,
        "sort": [
            {
                sort_field: {
                    "order": order,
                },
            },
        ],
        "from": (page_number - 1) * page_size,
        "size": page_size,
    }


def build_searched_films_body(
    query: str,
    page_number: int,
    page_size: int,
) -> dict[str, Any]:
    """Формирует полнотекстовый запрос Elasticsearch для поиска фильмов."""
    normalized_query = query.strip().lower()

    return {
        "_source": ["uuid", "title", "imdb_rating"],
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": normalized_query,
                            "fields": [
                                "title^5",
                                "description",
                            ],
                            "fuzziness": "AUTO",
                        },
                    },
                    {
                        "nested": {
                            "path": "actors",
                            "query": {
                                "match": {
                                    "actors.full_name": {
                                        "query": normalized_query,
                                        "fuzziness": "AUTO",
                                        "boost": 2,
                                    },
                                },
                            },
                        },
                    },
                    {
                        "nested": {
                            "path": "writers",
                            "query": {
                                "match": {
                                    "writers.full_name": {
                                        "query": normalized_query,
                                        "fuzziness": "AUTO",
                                        "boost": 2,
                                    },
                                },
                            },
                        },
                    },
                    {
                        "nested": {
                            "path": "directors",
                            "query": {
                                "match": {
                                    "directors.full_name": {
                                        "query": normalized_query,
                                        "fuzziness": "AUTO",
                                        "boost": 2,
                                    },
                                },
                            },
                        },
                    },
                ],
                "minimum_should_match": 1,
            },
        },
        "from": (page_number - 1) * page_size,
        "size": page_size,
    }


def build_similar_films_body(
    use_more_like_this: bool,
    film_id: str,
    genre_uuids: list[str],
    page_number: int,
    page_size: int,
    index_name: str,
) -> dict[str, Any]:
    """Формирует запрос поиска фильмов по жанрам и,
    при необходимости, содержимому."""
    bool_query: dict[str, Any] = {
        "filter": [
            {
                "nested": {
                    "path": "genre",
                    "query": {
                        "terms": {
                            "genre.uuid": genre_uuids,
                        },
                    },
                },
            },
        ],
        "must_not": [
            {
                "term": {
                    "uuid": film_id,
                },
            },
        ],
    }
    if use_more_like_this:
        bool_query["must"] = [
            {
                "more_like_this": {
                    "fields": [
                        "title",
                        "description",
                    ],
                    "like": [
                        {
                            "_index": index_name,
                            "_id": film_id,
                        },
                    ],
                    "min_term_freq": 1,
                    "min_doc_freq": 1,
                    "max_query_terms": 25,
                },
            },
        ]

    return {
        "_source": ["uuid", "title", "imdb_rating"],
        "query": {
            "bool": bool_query,
        },
        "sort": [
            {
                "_score": {
                    "order": "desc",
                },
            },
            {
                "imdb_rating": {
                    "order": "desc",
                },
            },
        ],
        "from": (page_number - 1) * page_size,
        "size": page_size,
    }
