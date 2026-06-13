"""Модуль бизнес-логики для работы с жанрами."""
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from core.config import get_settings
from db.elastic import get_elastic
from db.redis import get_redis
from models.genre import Genre

from services.cache_keys.genres import (
    _get_genre_cache_key,
    _get_genres_cache_key,
)

from services.cache import (
    put_model_to_cache,
    put_models_to_cache,
    get_model_from_cache,
    get_models_from_cache,
)

from services.bodies.genres import build_genres_body

settings = get_settings()


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
        genre_cache_key = _get_genre_cache_key(genre_id)

        genre = await get_model_from_cache(
            redis=self.redis,
            key=genre_cache_key,
            model=Genre,
        )

        if genre is None:
            genre = await self._get_genre_from_elastic(genre_id)
            if genre is None:
                return None

            await put_model_to_cache(
                redis=self.redis,
                key=genre_cache_key,
                value=genre,
                ttl=settings.genre_cache_expire_in_seconds,
            )

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

        genres_cache_key = _get_genres_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        genres = await get_models_from_cache(
            redis=self.redis,
            key=genres_cache_key,
            model=Genre,
        )
        if genres is not None:
            return genres

        genres = await self._get_genres_from_elastic(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await put_models_to_cache(
            redis=self.redis,
            key=genres_cache_key,
            values=genres,
            ttl=settings.genre_cache_expire_in_seconds,
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
        body = build_genres_body(
            query=query,
            sort=sort,
            page_number=page_number,
            page_size=page_size,
            genre_sort_fields=settings.genre_sort_fields,
        )

        response = await self.elastic.search(index='genres', body=body)
        return [
            Genre.model_validate(hit['_source'])
            for hit in response['hits']['hits']
        ]


@lru_cache()
def get_genre_service(
    redis: Redis = Depends(get_redis),  # noqa: B008
    elastic: AsyncElasticsearch = Depends(get_elastic),  # noqa: B008
) -> GenreService:
    """Возвращает экземпляр GenreService."""
    return GenreService(redis, elastic)
