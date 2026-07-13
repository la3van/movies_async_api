"""Модуль настроек приложения."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки FastAPI-сервиса."""
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    project_name: str = 'movies-async-api'

    # Elasticsearch
    elastic_host: str = 'localhost'
    elastic_port: int = 9200
    elastic_request_timeout: int = 30

    elastic_movies_index: str = 'movies'
    elastic_genres_index: str = 'genres'
    elastic_persons_index: str = 'persons'

    # Elasticsearch retries
    elastic_max_retries: int = 2
    elastic_retry_on_timeout: bool = True
    elastic_retry_on_status: tuple[int, ...] = (
        429,
        502,
        503,
        504,
    )
    elastic_retry_backoff_base: float = 0.1
    elastic_retry_backoff_cap: float = 1.0

    # FilmService
    film_sort_fields: dict[str, str]
    film_cache_expire_in_seconds: int = 300

    # GenreService
    genre_sort_fields: dict[str, str]
    genre_cache_expire_in_seconds: int = 300

    # PersonService
    person_sort_fields: dict[str, str]
    person_cache_expire_in_seconds: int = 300

    # Redis
    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_db: int = 0
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5

    # Redis retries
    redis_max_retries: int = 2
    redis_retry_backoff_base: float = 0.1
    redis_retry_backoff_cap: float = 1.0

    @property
    def elastic_url(self) -> str:
        """Возвращает URL Elasticsearch."""
        return f'http://{self.elastic_host}:{self.elastic_port}'


@lru_cache()
def get_settings() -> Settings:
    """Возвращает настройки приложения."""
    return Settings()
