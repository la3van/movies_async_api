"""Модуль настроек ETL-сервиса"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE_DIR = Path(__file__).resolve().parent


def get_default_mappings_dir() -> Path:
    """Возвращает путь к Elasticsearch mappings."""
    for parent in MODULE_DIR.parents:
        mappings_dir = parent / "infrastructure" / "elasticsearch" / "mappings"

        if mappings_dir.is_dir():
            return mappings_dir

    return Path("/app/mappings")


DEFAULT_MAPPINGS_DIR = get_default_mappings_dir()


class Settings(BaseSettings):
    """Настройки ETL-сервиса PostgreSQL -> Elasticsearch."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "content-etl"

    # PostgreSQL
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_options: str = "-c search_path=public,content"
    postgres_connect_timeout: int = 5
    postgres_statement_timeout_ms: int = 30000

    # Elasticsearch
    elastic_host: str
    elastic_port: int
    elastic_request_timeout: int = 30
    movies_index: str = "movies"
    genres_index: str = "genres"
    persons_index: str = "persons"

    # Redis
    redis_host: str
    redis_port: int
    redis_db: int = 0
    redis_state_key_prefix: str = "etl_state"
    redis_socket_connect_timeout: int = 5
    redis_socket_timeout: int = 5

    # ETL
    batch_size: int = 100
    etl_sleep_time: int = 1

    # Backoff
    backoff_start_sleep_time: float = 0.1
    backoff_factor: int = 2
    backoff_border_sleep_time: int = 10
    backoff_jitter: bool = True

    schemas_dir: Path = DEFAULT_MAPPINGS_DIR

    @property
    def elastic_url(self) -> str:
        """Возвращает URL Elasticsearch."""
        return f"http://{self.elastic_host}:{self.elastic_port}"

    @property
    def postgres_connection_params(self) -> dict[str, Any]:
        """Возвращает параметры подключения к PostgreSQL."""
        options = " ".join(
            option
            for option in (
                self.postgres_options.strip(),
                (f"-c statement_timeout={self.postgres_statement_timeout_ms}"),
            )
            if option
        )
        return {
            "host": self.postgres_host,
            "port": self.postgres_port,
            "dbname": self.postgres_db,
            "user": self.postgres_user,
            "password": self.postgres_password,
            "options": options,
            "connect_timeout": self.postgres_connect_timeout,
        }

    def get_state_key(self, pipeline_name: str) -> str:
        """Возвращает Redis-ключ состояния для конкретного пайплайна."""
        return f"{self.redis_state_key_prefix}:{pipeline_name}"


@lru_cache
def get_settings() -> Settings:
    """Возвращает настройки ETL-сервиса."""
    return Settings()
