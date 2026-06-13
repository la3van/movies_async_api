"""Модуль бизнес-логики для работы с персонами."""
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from core.config import get_settings
from db.elastic import get_elastic
from db.redis import get_redis
from models.film import ShortFilm
from models.person import Person

from services.cache_keys.persons import (
    _get_person_cache_key,
    _get_persons_cache_key,
    _get_person_films_cache_key,
)

from services.cache import (
    get_model_from_cache,
    get_models_from_cache,
    put_model_to_cache,
    put_models_to_cache,
)

from services.bodies.persons import (
    build_persons_body,
    build_person_films_body,
)

settings = get_settings()


class PersonService:
    """Сервис для получения информации о персонах.

    Поддерживает получение персоны по id, получение списка персон
    с учётом поиска, сортировки и пагинации, а также кеширование
    результатов в Redis.
    """

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_person_by_id(self, person_id: str) -> Optional[Person]:
        """Возвращает персону по id или None, если персона не найдена."""
        person_cache_key = _get_person_cache_key(person_id)

        person = await get_model_from_cache(
            redis=self.redis,
            key=person_cache_key,
            model=Person,
        )

        if person is None:
            person = await self._get_person_from_elastic(person_id)
            if person is None:
                return None

            await put_model_to_cache(
                redis=self.redis,
                key=person_cache_key,
                value=person,
                ttl=settings.person_cache_expire_in_seconds,
            )

        return person

    async def get_persons(
        self,
        query: str | None = None,
        sort: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[Person]:
        """Возвращает список персон с учётом поиска, сортировки и пагинации."""
        normalized_query = query.strip() if query else None
        if not normalized_query:
            normalized_query = None

        effective_sort = sort
        if effective_sort is None and normalized_query is None:
            effective_sort = 'full_name'

        persons_cache_key = _get_persons_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        persons = await get_models_from_cache(
            redis=self.redis,
            key=persons_cache_key,
            model=Person,
        )

        if persons is not None:
            return persons

        persons = await self._get_persons_from_elastic(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await put_models_to_cache(
            redis=self.redis,
            key=persons_cache_key,
            values=persons,
            ttl=settings.person_cache_expire_in_seconds,
        )

        return persons

    async def get_person_films(
        self,
        person_id: str,
        page_number: int = 1,
        page_size: int = 50,
    ) -> Optional[list[ShortFilm]]:
        """Возвращает фильмы, связанные с персоной.

        Если персона не найдена, возвращается None."""
        person = await self.get_person_by_id(person_id)
        if person is None:
            return None

        person_films_cache_key = _get_person_films_cache_key(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )

        films = await get_models_from_cache(
            redis=self.redis,
            key=person_films_cache_key,
            model=ShortFilm,
        )
        if films is not None:
            return films

        films = await self._get_person_films_from_elastic(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )
        await put_models_to_cache(
            redis=self.redis,
            key=person_films_cache_key,
            values=films,
            ttl=settings.person_cache_expire_in_seconds,
        )

        return films

    async def _get_person_from_elastic(
        self,
        person_id: str,
    ) -> Optional[Person]:
        """Получает персону из Elasticsearch по id."""
        try:
            doc = await self.elastic.get(index='persons', id=person_id)
        except NotFoundError:
            return None
        return Person.model_validate(doc['_source'])

    async def _get_persons_from_elastic(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Person]:
        """Получает список персон из Elasticsearch."""
        body = build_persons_body(
            query=query,
            sort=sort,
            page_number=page_number,
            page_size=page_size,
            person_sort_fields=settings.person_sort_fields,
        )

        response = await self.elastic.search(index='persons', body=body)
        return [
            Person.model_validate(hit['_source'])
            for hit in response['hits']['hits']
        ]

    async def _get_person_films_from_elastic(
        self,
        person_id: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет фильмы, где персона указана актёром, сценаристом
        или режиссёром."""
        body = build_person_films_body(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )

        response = await self.elastic.search(index='movies', body=body)

        return [
            self._build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    def _build_short_film(self, source: dict) -> ShortFilm:
        """Собирает краткую модель фильма из данных Elasticsearch."""
        return ShortFilm(
            uuid=source['uuid'],
            title=source['title'],
            imdb_rating=source.get('imdb_rating'),
        )


@lru_cache()
def get_person_service(
    redis: Redis = Depends(get_redis),  # noqa: B008
    elastic: AsyncElasticsearch = Depends(get_elastic),  # noqa: B008
) -> PersonService:
    """Возвращает экземпляр PersonService."""
    return PersonService(redis, elastic)
