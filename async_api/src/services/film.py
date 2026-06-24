"""Модуль бизнес-логики для работы с фильмами."""
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from core.config import get_settings
from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film, ShortFilm

from services.cache_keys.films import (
    get_film_cache_key,
    get_sorted_films_cache_key,
    get_searched_films_cache_key,
    get_similar_films_cache_key,
)

from services.cache import (
    put_model_to_cache,
    put_models_to_cache,
    get_model_from_cache,
    get_models_from_cache,
)

from services.bodies.films import (
    build_sorted_films_body,
    build_searched_films_body,
    build_similar_films_body,
)

from services.mappers.films import (
    build_short_film
)

settings = get_settings()


class FilmService:
    """Сервис для получения информации о фильмах.

    Поддерживает получение фильма по id, получение списка фильмов
    с сортировкой и фильтрацией по жанру, а также полнотекстовый
    поиск фильмов.
    """

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_film_by_id(self, film_id: str) -> Optional[Film]:
        """Возвращает фильм по id или None, если фильм не найден."""
        film_cache_key = get_film_cache_key(film_id)

        film = await get_model_from_cache(
            redis=self.redis,
            key=film_cache_key,
            model=Film,
        )

        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await put_model_to_cache(
                redis=self.redis,
                key=film_cache_key,
                value=film,
                ttl=settings.film_cache_expire_in_seconds,
            )

        return film

    async def get_sorted_films(
        self,
        sort: str = '-imdb_rating',
        genre_filter: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[ShortFilm]:
        """Возвращает список фильмов с сортировкой, пагинацией и фильтром по
        жанру."""
        sorted_films_cache_key = get_sorted_films_cache_key(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )

        sorted_films = await get_models_from_cache(
            redis=self.redis,
            key=sorted_films_cache_key,
            model=ShortFilm,
        )
        if sorted_films is not None:
            return sorted_films

        sorted_films = await self._get_sorted_films_from_elastic(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )
        await put_models_to_cache(
            redis=self.redis,
            key=sorted_films_cache_key,
            values=sorted_films,
            ttl=settings.film_cache_expire_in_seconds,
        )

        return sorted_films

    async def get_searched_films(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает фильмы, найденные по полнотекстовому поисковому
        запросу."""
        searched_films_cache_key = get_searched_films_cache_key(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

        searched_films = await get_models_from_cache(
            redis=self.redis,
            key=searched_films_cache_key,
            model=ShortFilm,
        )
        if searched_films is not None:
            return searched_films

        searched_films = await self._get_searched_films_from_elastic(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )
        await put_models_to_cache(
            redis=self.redis,
            key=searched_films_cache_key,
            values=searched_films,
            ttl=settings.film_cache_expire_in_seconds,
        )

        return searched_films

    async def get_similar_films(
        self,
        film_id: str,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[ShortFilm]:
        """Возвращает фильмы, похожие на данный(без учета film_id)
        схожесть считается через 'more_like_this' в Elasticsearch."""
        similar_films_cache_key = get_similar_films_cache_key(
            film_id=film_id,
            page_number=page_number,
            page_size=page_size,
        )

        similar_films = await get_models_from_cache(
            redis=self.redis,
            key=similar_films_cache_key,
            model=ShortFilm,
        )
        if similar_films is not None:
            return similar_films

        film = await self.get_film_by_id(film_id)

        genre_uuids = []
        if film is not None:
            genre_uuids = [
                genre.uuid
                for genre in film.genre
            ]
        if not genre_uuids:
            return []

        similar_films = await self._get_similar_films_from_elastic(
            use_more_like_this=True,
            film_id=film_id,
            genre_uuids=genre_uuids,
            page_number=page_number,
            page_size=page_size,
        )

        if not similar_films:
            similar_films = await self._get_similar_films_from_elastic(
                use_more_like_this=False,
                film_id=film_id,
                genre_uuids=genre_uuids,
                page_number=page_number,
                page_size=page_size,
            )

        await put_models_to_cache(
            redis=self.redis,
            key=similar_films_cache_key,
            values=similar_films,
            ttl=settings.film_cache_expire_in_seconds,
        )

        return similar_films

    async def _get_film_from_elastic(self, film_id: str) -> Optional[Film]:
        """Получает фильм из Elasticsearch по id."""
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        return Film.model_validate(doc['_source'])

    async def _get_sorted_films_from_elastic(
        self,
        sort: str,
        genre_filter: str | None,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Получает из Elasticsearch список фильмов с сортировкой и фильтром
        по жанру."""
        body = build_sorted_films_body(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
            film_sort_fields=settings.film_sort_fields,
        )

        response = await self.elastic.search(index='movies', body=body)
        return [
            self._build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def _get_searched_films_from_elastic(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет фильмы в Elasticsearch по названию, описанию и именам
        участников."""
        body = build_searched_films_body(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

        response = await self.elastic.search(index='movies', body=body)
        return [
            self._build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def _get_similar_films_from_elastic(
        self,
        use_more_like_this: bool,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет похожие фильмы с ограничением по жанрам
        параметр more_like_this учитывается в зависимости от флага
        elastic_search_flag."""
        body = build_similar_films_body(
            use_more_like_this=use_more_like_this,
            film_id=film_id,
            genre_uuids=genre_uuids,
            page_number=page_number,
            page_size=page_size,
        )

        response = await self.elastic.search(index='movies', body=body)

        return [
            build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]


@lru_cache()
def get_film_service(
    redis: Redis = Depends(get_redis),  # noqa: B008
    elastic: AsyncElasticsearch = Depends(get_elastic),  # noqa: B008
) -> FilmService:
    """Возвращает экземпляр FilmService."""
    return FilmService(redis, elastic)
