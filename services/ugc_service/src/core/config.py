"""Настройки UGC Service."""

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, внешних сервисов и хранилищ."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_name: str = "ugc-service"
    api_version: str = "1.0.0"
    max_request_body_bytes: int = 65_536

    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_database: str = "ugc"
    mongo_username: str | None = None
    mongo_password: str | None = None
    mongo_auth_database: str = "admin"
    mongo_connect_timeout_ms: int = 2_000
    mongo_server_selection_timeout_ms: int = 2_000
    mongo_socket_timeout_ms: int = 5_000
    mongo_wait_queue_timeout_ms: int = 2_000
    mongo_operation_timeout_ms: int = 5_000
    mongo_max_pool_size: int = 100
    mongo_min_pool_size: int = 0

    mongo_replica_set: str = "rs0"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 4
    redis_socket_connect_timeout: float = 1.0
    redis_socket_timeout: float = 1.0
    redis_max_retries: int = 2
    redis_retry_backoff_base: float = 0.1
    redis_retry_backoff_cap: float = 1.0
    rate_limit_enabled: bool = True
    rate_limit_key_prefix: str = "ugc:rate_limit"

    auth_service_host: str = "auth-service"
    auth_service_port: int = 8000
    auth_service_api_prefix: str = "/api/v1"
    auth_service_connect_timeout: float = 1.0
    auth_service_read_timeout: float = 2.0

    content_service_host: str = "content-service"
    content_service_port: int = 8000
    content_service_api_prefix: str = "/api/v1"
    content_service_connect_timeout: float = 1.0
    content_service_read_timeout: float = 2.0
    content_validate_films: bool = True

    review_sort_fields: dict[str, str] = {
        "published_at": "created_at",
        "updated_at": "updated_at",
        "likes": "likes",
        "dislikes": "dislikes",
        "helpfulness": "helpfulness",
        "author_rating": "author_rating",
    }

    @property
    def mongo_uri(self) -> str:
        """Собрать MongoDB URI без вывода учётных данных в логи."""
        credentials = ""
        if self.mongo_username is not None:
            username = quote_plus(self.mongo_username)
            password = quote_plus(self.mongo_password or "")
            credentials = f"{username}:{password}@"

        return (
            f"mongodb://{credentials}{self.mongo_host}:{self.mongo_port}/"
            f"?authSource={quote_plus(self.mongo_auth_database)}"
            f"&replicaSet={quote_plus(self.mongo_replica_set)}"
        )

    @property
    def auth_service_base_url(self) -> str:
        """Вернуть внутренний URL Auth Service."""
        prefix = self.auth_service_api_prefix.strip("/")
        return f"http://{self.auth_service_host}:{self.auth_service_port}/{prefix}/"

    @property
    def content_service_base_url(self) -> str:
        """Вернуть внутренний URL Content Service."""
        prefix = self.content_service_api_prefix.strip("/")
        return f"http://{self.content_service_host}:{self.content_service_port}/{prefix}/"


@lru_cache
def get_settings() -> Settings:
    """Вернуть кешированный объект настроек."""
    return Settings()
