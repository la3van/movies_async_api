"""Функции сборки зависимостей FastAPI-приложения."""

from typing import Annotated

from cache.base import Cache
from cache.redis import RedisCache
from core.config import Settings, get_settings
from db.elastic import get_elastic
from db.redis import get_redis
from elasticsearch import AsyncElasticsearch
from fastapi import Depends
from redis.asyncio import Redis
from repositories.elastic.film import ElasticsearchFilmRepository
from repositories.elastic.genre import ElasticsearchGenreRepository
from repositories.elastic.person import ElasticsearchPersonRepository
from repositories.interfaces.film import FilmRepository
from repositories.interfaces.genre import GenreRepository
from repositories.interfaces.person import PersonRepository
from services.film import FilmService
from services.genre import GenreService
from services.person import PersonService


def get_cache(
    redis: Annotated[Redis, Depends(get_redis)],
) -> Cache:
    """Создаёт кеш приложения на основе Redis."""
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
    """Создаёт Elasticsearch-репозиторий фильмов."""
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
    """Создаёт Elasticsearch-репозиторий жанров."""
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
    """Создаёт Elasticsearch-репозиторий персон."""
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
    """Создаёт сервис работы с фильмами."""
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
    """Создаёт сервис работы с жанрами."""
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
    """Создаёт сервис работы с персонами."""
    return PersonService(
        repository=repository,
        cache=cache,
        cache_ttl=settings.person_cache_expire_in_seconds,
    )
