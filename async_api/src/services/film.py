"""Модуль бизнес-логики для работы с фильмами."""
import json
from functools import lru_cache
from typing import Optional

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from db.elastic import get_elastic
from db.redis import get_redis
from models.film import Film, ShortFilm

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5
FILM_SORT_FIELDS = {
    'imdb_rating': 'imdb_rating',
}


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
        film_cache_key = self._get_film_cache_key(film_id)

        film = await self._get_film_from_cache(film_cache_key)

        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film_cache_key, film)

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
        sorted_films_cache_key = self._get_sorted_films_cache_key(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )

        sorted_films = await self._get_short_films_from_cache(
            sorted_films_cache_key,
        )
        if sorted_films is not None:
            return sorted_films

        sorted_films = await self._get_sorted_films_from_elastic(
            sort=sort,
            genre_filter=genre_filter,
            page_number=page_number,
            page_size=page_size,
        )
        await self._put_short_films_to_cache(
            films_cache_key=sorted_films_cache_key,
            films=sorted_films,
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
        searched_films_cache_key = self._get_searched_films_cache_key(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )

        searched_films = await self._get_short_films_from_cache(
            searched_films_cache_key,
        )
        if searched_films is not None:
            return searched_films

        searched_films = await self._get_searched_films_from_elastic(
            query=query,
            page_number=page_number,
            page_size=page_size,
        )
        await self._put_short_films_to_cache(
            films_cache_key=searched_films_cache_key,
            films=searched_films,
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
        similar_films_cache_key = self._get_similar_films_cache_key(
            film_id=film_id,
            page_number=page_number,
            page_size=page_size,
        )

        similar_films = await self._get_short_films_from_cache(
            similar_films_cache_key,
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

        await self._put_short_films_to_cache(
            films_cache_key=similar_films_cache_key,
            films=similar_films,
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
        order = 'desc' if sort.startswith('-') else 'asc'
        sort_field = FILM_SORT_FIELDS.get(sort.lstrip('-'), 'imdb_rating')

        search_query: dict = {
            'match_all': {},
        }

        if genre_filter:
            search_query = {
                'bool': {
                    'filter': [
                        {
                            'nested': {
                                'path': 'genre',
                                'query': {
                                    'term': {
                                        'genre.uuid': genre_filter,
                                    },
                                },
                            },
                        },
                    ],
                },
            }

        body = {
            '_source': ['uuid', 'title', 'imdb_rating'],
            'query': search_query,
            'sort': [
                {
                    sort_field: {
                        'order': order,
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

    async def _get_searched_films_from_elastic(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет фильмы в Elasticsearch по названию, описанию и именам
        участников."""
        normalized_query = query.strip().lower()

        body = {
            '_source': ['uuid', 'title', 'imdb_rating'],
            'query': {
                'bool': {
                    'should': [
                        {
                            'multi_match': {
                                'query': normalized_query,
                                'fields': [
                                    'title^5',
                                    'description',
                                ],
                                'fuzziness': 'AUTO',
                            },
                        },
                        {
                            'nested': {
                                'path': 'actors',
                                'query': {
                                    'match': {
                                        'actors.full_name': {
                                            'query': normalized_query,
                                            'fuzziness': 'AUTO',
                                            'boost': 2,
                                        },
                                    },
                                },
                            },
                        },
                        {
                            'nested': {
                                'path': 'writers',
                                'query': {
                                    'match': {
                                        'writers.full_name': {
                                            'query': normalized_query,
                                            'fuzziness': 'AUTO',
                                            'boost': 2,
                                        },
                                    },
                                },
                            },
                        },
                        {
                            'nested': {
                                'path': 'directors',
                                'query': {
                                    'match': {
                                        'directors.full_name': {
                                            'query': normalized_query,
                                            'fuzziness': 'AUTO',
                                            'boost': 2,
                                        },
                                    },
                                },
                            },
                        },
                    ],
                    'minimum_should_match': 1,
                },
            },
            'from': (page_number - 1) * page_size,
            'size': page_size,
        }

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
        bool_query = {
            'filter': [
                {
                    'nested': {
                        'path': 'genre',
                        'query': {
                            'terms': {
                                'genre.uuid': genre_uuids,
                            },
                        },
                    },
                },
            ],
            'must_not': [
                {
                    'term': {
                        'uuid': film_id,
                    },
                },
            ],
        }
        if use_more_like_this:
            bool_query['must'] = [
                        {
                            'more_like_this': {
                                'fields': [
                                    'title',
                                    'description',
                                ],
                                'like': [
                                    {
                                        '_index': 'movies',
                                        '_id': film_id,
                                    },
                                ],
                                'min_term_freq': 1,
                                'min_doc_freq': 1,
                                'max_query_terms': 25,
                            },
                        },
                    ]

        body = {
            '_source': ['uuid', 'title', 'imdb_rating'],
            'query': {
                'bool': bool_query,
            },
            'sort': [
                {
                    '_score': {
                        'order': 'desc',
                    },
                },
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

    def _get_film_cache_key(self, film_id: str) -> str:
        """Формирует ключ кеша для одного фильма."""
        return f'film:{film_id}'

    def _get_sorted_films_cache_key(
        self,
        sort: str,
        genre_filter: str | None,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формирует ключ кеша для списка фильмов с учётом сортировки,
        жанра и пагинации."""
        normalized_genre_filter = (
            genre_filter.strip() if genre_filter is not None else 'all'
        )
        return (
            f'films:sort={sort}:genre={normalized_genre_filter}:'
            f'page={page_number}:size={page_size}'
        )

    def _get_searched_films_cache_key(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формирует ключ кеша для результата
        полнотекстового поиска фильмов(нормализуем query)."""
        normalized_query = query.strip().lower()
        return (
            f'films:query={normalized_query}:'
            f'page_number={page_number}:page_size={page_size}'
        )

    def _get_similar_films_cache_key(
        self,
        film_id: str,
        page_number: int,
        page_size: int,
    ) -> str:
        """Формируем ключ кэша для похожих фильмов."""
        return (
            f'films:similar:film={film_id}:'
            f'page={page_number}:size={page_size}'
        )

    async def _get_film_from_cache(
        self,
        film_cache_key: str,
    ) -> Optional[Film]:
        """Получает фильм из кеша по ключу."""
        data = await self.redis.get(film_cache_key)
        if not data:
            return None

        film = Film.model_validate_json(data)
        return film

    async def _get_short_films_from_cache(
        self,
        films_cache_key: str,
    ) -> Optional[list[ShortFilm]]:
        """Получает список фильмов из кеша по ключу."""
        data = await self.redis.get(films_cache_key)

        if not data:
            return None

        raw_films = json.loads(data)
        return [
            ShortFilm.model_validate(raw_film)
            for raw_film in raw_films
        ]

    async def _put_film_to_cache(
        self,
        film_cache_key: str,
        film: Film,
    ) -> None:
        """Сохраняет фильм в кеш с ограниченным временем жизни."""
        await self.redis.set(
            film_cache_key,
            film.model_dump_json(),
            ex=FILM_CACHE_EXPIRE_IN_SECONDS,
        )

    async def _put_short_films_to_cache(
        self,
        films_cache_key: str,
        films: list[ShortFilm],
    ) -> None:
        """Сохраняет список фильмов в кеш с ограниченным временем жизни."""
        await self.redis.set(
            films_cache_key,
            json.dumps([film.model_dump(mode='json') for film in films]),
            ex=FILM_CACHE_EXPIRE_IN_SECONDS,
        )

    def _build_short_film(self, source: dict) -> ShortFilm:
        """Собирает краткую модель фильма из данных Elasticsearch."""
        return ShortFilm(
            uuid=source['uuid'],
            title=source['title'],
            imdb_rating=source.get('imdb_rating'),
        )


@lru_cache()
def get_film_service(
    redis: Redis = Depends(get_redis),  # noqa: B008
    elastic: AsyncElasticsearch = Depends(get_elastic),  # noqa: B008
) -> FilmService:
    """Возвращает экземпляр FilmService."""
    return FilmService(redis, elastic)
