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

    @property
    def elastic_url(self) -> str:
        """Возвращает URL Elasticsearch."""
        return f'http://{self.elastic_host}:{self.elastic_port}'


@lru_cache()
def get_settings() -> Settings:
    """Возвращает настройки приложения."""
    return Settings()
