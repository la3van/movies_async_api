"""Модуль бизнес-логики для работы с жанрами."""

import json
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre

GENRE_CACHE_EXPIRE_IN_SECONDS = 60 * 5
GENRE_SORT_FIELDS = {
    'name': 'name.raw',
}


class GenreService:
    """Сервис для получения информации о жанрах.

    Поддерживает получение жанра по id, получение списка жанров
    с учётом поиска, сортировки и пагинации, а также кеширование
    результатов в Redis.
    """

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_genre_by_id(self, genre_id: str) -> Optional[Genre]:
        """Возвращает жанр по id или None, если жанр не найден."""
        genre_cache_key = self._get_genre_cache_key(genre_id)

        genre = await self._get_genre_from_cache(genre_cache_key)

        if genre is None:
            genre = await self._get_genre_from_elastic(genre_id)
            if genre is None:
                return None

            await self._put_genre_to_cache(genre_cache_key, genre)

        return genre

    async def get_genres(
        self,
        query: str | None = None,
        sort: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[Genre]:
        """Возвращает список жанров с учётом поиска, сортировки и пагинации."""
        normalized_query = query.strip() if query else None
        if not normalized_query:
            normalized_query = None

        effective_sort = sort
        if effective_sort is None and normalized_query is None:
            effective_sort = 'name'

        genres_cache_key = self._get_genres_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        genres = await self._get_genres_from_cache(genres_cache_key)
        if genres is not None:
            return genres

        genres = await self._get_genres_from_elastic(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await self._put_genres_to_cache(
            genres_cache_key=genres_cache_key,
            genres=genres,
        )

        return genres

    async def _get_genre_from_elastic(self, genre_id: str) -> Optional[Genre]:
        """Получает жанр из Elasticsearch по id."""
        try:
            doc = await self.elastic.get(index='genres', id=genre_id)
        except NotFoundError:
            return None
        return Genre.model_validate(doc['_source'])

    async def _get_genres_from_elastic(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Genre]:
        """Получает список жанров из Elasticsearch."""
        search_query: dict = {
            'match_all': {},
        }
        if query:
            search_query = {
                'multi_match': {
                    'query': query,
                    'fields': [
                        'name^5',
                        'description',
                    ],
                },
            }

        body = {
            'query': search_query,
            'from': (page_number - 1) * page_size,
            'size': page_size,
        }

        if sort:
            order = 'desc' if sort.startswith('-') else 'asc'
            sort_field = GENRE_SORT_FIELDS.get(
                sort.lstrip('-'),
                'name.raw',
            )

            body['sort'] = [
                {
                    sort_field: {
                        'order': order,
                    },
                },
            ]

        response = await self.elastic.search(index='genres', body=body)
        return [
            Genre.model_validate(hit['_source'])
            for hit in response['hits']['hits']
        ]

    def _get_genre_cache_key(self, genre_id: str) -> str:
        """Формирует ключ кеша для одного жанра."""
        return f'genre:{genre_id}'

    def _get_genres_cache_key(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формирует ключ кеша для списка жанров.

        Ключ учитывает поисковый запрос, сортировку и параметры пагинации.
        """
        normalized_query = query.strip().lower() if query else 'all'
        normalized_sort = sort if sort else 'none'
        return (
            f'genres:query={normalized_query}:sort={normalized_sort}:'
            f'page_number={page_number}:page_size={page_size}'
        )

    async def _get_genre_from_cache(
        self,
        genre_cache_key: str,
    ) -> Optional[Genre]:
        """Получает жанр из кеша по ключу."""
        data = await self.redis.get(genre_cache_key)

        if not data:
            return None

        genre = Genre.model_validate_json(data)
        return genre

    async def _get_genres_from_cache(
        self,
        genres_cache_key: str,
    ) -> Optional[list[Genre]]:
        """Получает список жанров из кеша по ключу."""
        data = await self.redis.get(genres_cache_key)

        if not data:
            return None

        raw_genres = json.loads(data)
        return [
            Genre.model_validate(raw_genre)
            for raw_genre in raw_genres
        ]

    async def _put_genre_to_cache(
        self,
        genre_cache_key: str,
        genre: Genre,
    ) -> None:
        """Сохраняет жанр в кеш с ограниченным временем жизни."""
        await self.redis.set(
            genre_cache_key,
            genre.model_dump_json(),
            ex=GENRE_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _put_genres_to_cache(
        self,
        genres_cache_key: str,
        genres: list[Genre],
    ) -> None:
        """Сохраняет список жанров в кеш с ограниченным временем жизни."""
        await self.redis.set(
            genres_cache_key,
            json.dumps([genre.model_dump(mode='json') for genre in genres]),
            ex=GENRE_CACHE_EXPIRE_IN_SECONDS,
        )


@lru_cache()
def get_genre_service(
    redis: Redis = Depends(get_redis),  # noqa: B008
    elastic: AsyncElasticsearch = Depends(get_elastic),  # noqa: B008
) -> GenreService:
    """Возвращает экземпляр GenreService."""
    return GenreService(redis, elastic)
