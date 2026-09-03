"""Настройки окружения функциональных тестов."""

import json
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

FUNCTIONAL_DIR = Path(__file__).resolve().parent


def get_default_mappings_dir() -> Path:
    """Возвращает путь к Elasticsearch mappings.

    На хосте ищет infrastructure относительно корня репозитория.
    В Docker использует каталог, примонтированный в /app/mappings.
    """
    for parent in FUNCTIONAL_DIR.parents:
        mappings_dir = parent / "infrastructure" / "elasticsearch" / "mappings"

        if mappings_dir.is_dir():
            return mappings_dir

    return Path("/app/mappings")


DEFAULT_MAPPINGS_DIR = get_default_mappings_dir()


class TestSettings(BaseSettings):
    """Хранит настройки окружения функциональных тестов."""

    elastic_url: str = "http://elasticsearch:9200"
    redis_url: str = "redis://redis:6379/0"
    service_url: str = "http://async_api:8000"

    api_prefix: str = "/api/v1"

    es_movies_index: str = "movies"
    es_genres_index: str = "genres"
    es_persons_index: str = "persons"

    schemas_dir: Path = DEFAULT_MAPPINGS_DIR

    elastic_request_timeout: float = 5.0
    elastic_wait_timeout: float = 60.0
    elastic_wait_interval: float = 1.0

    redis_socket_connect_timeout: float = 2.0
    redis_socket_timeout: float = 2.0
    redis_wait_timeout: float = 30.0
    redis_wait_interval: float = 1.0

    http_request_timeout: float = 10.0

    jwt_secret_key: str = "functional_test_jwt_secret_key"
    jwt_algorithm: str = "HS256"

    model_config = SettingsConfigDict(
        env_file=FUNCTIONAL_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_elastic_url(self) -> str:
        """Возвращает URL тестового Elasticsearch."""
        return self.elastic_url

    def get_redis_url(self) -> str:
        """Возвращает URL тестового Redis."""
        return self.redis_url

    @property
    def es_movies_index_schema(self) -> dict[str, Any]:
        """Возвращает схему тестового индекса фильмов."""
        return self._load_index_schema("movies.json")

    @property
    def es_genres_index_schema(self) -> dict[str, Any]:
        """Возвращает схему тестового индекса жанров."""
        return self._load_index_schema("genres.json")

    @property
    def es_persons_index_schema(self) -> dict[str, Any]:
        """Возвращает схему тестового индекса персон."""
        return self._load_index_schema("persons.json")

    def _load_index_schema(
        self,
        filename: str,
    ) -> dict[str, Any]:
        """Загружает JSON-схему Elasticsearch из файла."""
        schema_path = self.schemas_dir / filename

        if not schema_path.is_file():
            raise FileNotFoundError(
                f"Elasticsearch schema not found: {schema_path}",
            )

        with schema_path.open(
            mode="r",
            encoding="utf-8",
        ) as schema_file:
            return json.load(schema_file)


test_settings = TestSettings()
