"""Модуль бизнес-логики для работы с персонами."""

import json
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import ShortFilm
from models.person import Person

PERSON_CACHE_EXPIRE_IN_SECONDS = 60 * 5
PERSON_SORT_FIELDS = {
    'full_name': 'full_name.raw',
}


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
        person_cache_key = self._get_person_cache_key(person_id)

        person = await self._get_person_from_cache(person_cache_key)

        if person is None:
            person = await self._get_person_from_elastic(person_id)
            if person is None:
                return None

            await self._put_person_to_cache(person_cache_key, person)

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

        persons_cache_key = self._get_persons_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        persons = await self._get_persons_from_cache(persons_cache_key)

        if persons is not None:
            return persons

        persons = await self._get_persons_from_elastic(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await self._put_persons_to_cache(
            persons_cache_key=persons_cache_key,
            persons=persons,
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

        person_films_cache_key = self._get_person_films_cache_key(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )

        films = await self._get_person_films_from_cache(
            person_films_cache_key=person_films_cache_key,
        )
        if films is not None:
            return films

        films = await self._get_person_films_from_elastic(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )
        await self._put_person_films_to_cache(
            person_films_cache_key=person_films_cache_key,
            films=films,
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
            sort_field = PERSON_SORT_FIELDS.get(
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

        response = await self.elastic.search(index='movies', body=body)

        return [
            self._build_short_film(hit['_source'])
            for hit in response['hits']['hits']
        ]

    def _get_person_cache_key(self, person_id: str) -> str:
        """Формирует ключ кеша для одной персоны."""
        return f'person:{person_id}'

    def _get_persons_cache_key(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формирует ключ кеша для списка персон.

        Ключ учитывает поисковый запрос, сортировку и параметры пагинации.
        """
        normalized_query = query.strip().lower() if query else 'all'
        normalized_sort = sort if sort else 'none'
        return (
            f'persons:query={normalized_query}:sort={normalized_sort}:'
            f'page_number={page_number}:page_size={page_size}'
        )

    def _get_person_films_cache_key(
        self,
        person_id: str,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формирует ключ кеша для списка фильмов персоны.

        Ключ учитывает id персоны и параметры пагинации."""
        return (
            f'person:films:person_id={person_id}:page_number={page_number}:'
            f'page_size={page_size}'
        )

    async def _get_person_from_cache(
        self,
        person_cache_key: str,
    ) -> Optional[Person]:
        """Получает персону из кеша по ключу."""
        data = await self.redis.get(person_cache_key)

        if not data:
            return None

        person = Person.model_validate_json(data)
        return person

    async def _get_persons_from_cache(
        self,
        persons_cache_key: str,
    ) -> Optional[list[Person]]:
        """Получает список персон из кеша по ключу."""
        data = await self.redis.get(persons_cache_key)

        if not data:
            return None

        raw_persons = json.loads(data)
        return [
            Person.model_validate(raw_person)
            for raw_person in raw_persons
        ]

    async def _get_person_films_from_cache(
        self,
        person_films_cache_key: str,
    ) -> Optional[list[ShortFilm]]:
        """Получает список фильмов персоны из кеша по ключу."""
        data = await self.redis.get(person_films_cache_key)

        if not data:
            return None

        raw_films = json.loads(data)
        return [
            ShortFilm.model_validate(raw_film)
            for raw_film in raw_films
        ]

    async def _put_person_to_cache(
        self,
        person_cache_key: str,
        person: Person,
    ) -> None:
        """Сохраняет персону в кеш с ограниченным временем жизни."""
        await self.redis.set(
            person_cache_key,
            person.model_dump_json(),
            ex=PERSON_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _put_persons_to_cache(
        self,
        persons_cache_key: str,
        persons: list[Person],
    ) -> None:
        """Сохраняет список персон в кеш с ограниченным временем жизни."""
        await self.redis.set(
            persons_cache_key,
            json.dumps([person.model_dump(mode='json') for person in persons]),
            ex=PERSON_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _put_person_films_to_cache(
        self,
        person_films_cache_key: str,
        films: list[ShortFilm],
    ) -> None:
        """Сохраняет список фильмов по персоне в кеш с ограничением
        времени жизни."""
        await self.redis.set(
            person_films_cache_key,
            json.dumps([film.model_dump(mode='json') for film in films]),
            ex=PERSON_CACHE_EXPIRE_IN_SECONDS,
        )

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
