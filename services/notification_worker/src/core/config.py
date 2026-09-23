"""Настройки приложения, загружаемые из окружения и файла .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки подключения, обработки сообщений и наблюдаемости."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+asyncpg://delivery:delivery@notification-postgres/deliveries"
    kafka_bootstrap_servers: str = "kafka-0:9092,kafka-1:9092,kafka-2:9092"
    jobs_topic: str = "notification-delivery-v1"
    dlq_topic: str = "notification-delivery-v1-dlq"
    consumer_group: str = "notification-worker-v1"
    auth_base_url: str = "http://auth-service:8000/api/v1/"
    poll_seconds: float = Field(default=1.0, gt=0)
    kafka_timeout_seconds: float = Field(default=20.0, gt=0, le=60)
    health_stale_seconds: float = Field(default=90.0, ge=60)

    internal_token: SecretStr = SecretStr("")
    results_topic: str = "notification-results-v1"
    events_topic: str = "cinema-events-v1"
    failed_topic: str = "notification-failed-v1"
    smtp_host: str = "mailpit"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_mode: Literal["plain", "starttls", "tls"] = "plain"
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_sender: str = "cinema@example.com"
    smtp_timeout: float = Field(default=20, ge=1, le=30)
    max_attempts: int = Field(default=5, ge=1, le=20)
    retry_base_seconds: int = Field(default=30, ge=1)
    retry_max_seconds: int = Field(default=3600, ge=1)
    lease_seconds: int = Field(default=180, ge=120)
    audience_page_size: int = Field(default=100, ge=1, le=500)
    sentry_dsn: str = ""
    otel_endpoint: str = ""
    service_name: str = "notifications"


@lru_cache
def get_settings() -> Settings:
    """Возвращает закешированный экземпляр настроек приложения."""
    return Settings()
