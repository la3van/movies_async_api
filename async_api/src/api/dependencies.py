from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import Depends
from redis.asyncio import Redis

from cache.base import Cache
from cache.redis import RedisCache

from db.elastic import get_elastic
from db.redis import get_redis

from repositories.elastic.film import ElasticsearchFilmRepository
from repositories.elastic.genre import ElasticsearchGenreRepository
from repositories.elastic.person import ElasticsearchPersonRepository

from repositories.interfaces.film import FilmRepository
from repositories.interfaces.genre import GenreRepository
from repositories.interfaces.person import PersonRepository

from services.film import FilmService
from services.genre import GenreService
from services.person import PersonService

from core.config import Settings, get_settings


def get_cache(
    redis: Annotated[Redis, Depends(get_redis)],
) -> Cache:
    return RedisCache(redis)


def get_film_repository(
    elastic: Annotated[
        AsyncElasticsearch,
        Depends(get_elastic),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> FilmRepository:
    return ElasticsearchFilmRepository(
        elastic=elastic,
        index_name=settings.elastic_movies_index,
        film_sort_fields=settings.film_sort_fields,
    )


def get_genre_repository(
    elastic: Annotated[
        AsyncElasticsearch,
        Depends(get_elastic),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> GenreRepository:
    return ElasticsearchGenreRepository(
        elastic=elastic,
        index_name=settings.elastic_genres_index,
        genre_sort_fields=settings.genre_sort_fields,
    )


def get_person_repository(
    elastic: Annotated[
        AsyncElasticsearch,
        Depends(get_elastic),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> PersonRepository:
    return ElasticsearchPersonRepository(
        elastic=elastic,
        persons_index_name=settings.elastic_persons_index,
        movies_index_name=settings.elastic_movies_index,
        person_sort_fields=settings.person_sort_fields,
    )


def get_film_service(
    repository: Annotated[
        FilmRepository,
        Depends(get_film_repository),
    ],
    cache: Annotated[
        Cache,
        Depends(get_cache),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> FilmService:
    return FilmService(
        repository=repository,
        cache=cache,
        cache_ttl=settings.film_cache_expire_in_seconds,
    )


def get_genre_service(
    repository: Annotated[
        GenreRepository,
        Depends(get_genre_repository),
    ],
    cache: Annotated[
        Cache,
        Depends(get_cache),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> GenreService:
    return GenreService(
        repository=repository,
        cache=cache,
        cache_ttl=settings.genre_cache_expire_in_seconds,
    )


def get_person_service(
    repository: Annotated[
        PersonRepository,
        Depends(get_person_repository),
    ],
    cache: Annotated[
        Cache,
        Depends(get_cache),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> PersonService:
    return PersonService(
        repository=repository,
        cache=cache,
        cache_ttl=settings.person_cache_expire_in_seconds,
    )
