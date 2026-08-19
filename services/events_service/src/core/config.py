"""Настройки сервиса сбора пользовательских событий."""
from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса сбора пользовательских событий."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    project_name: str = "events-service"
    max_event_request_bytes: int = 65_536

    # Kafka
    kafka_bootstrap_servers: str = (
        "kafka-0:9092,"
        "kafka-1:9092,"
        "kafka-2:9092"
    )

    kafka_topic: str = "user-events"
    kafka_client_id: str = "events-service"

    kafka_acks: str = "all"
    kafka_enable_idempotence: bool = True
    kafka_linger_ms: int = 5
    kafka_compression_type: str = "lz4"

    kafka_delivery_timeout_ms: int = 5_000
    kafka_ack_timeout_seconds: float = 6.0
    kafka_metadata_timeout_seconds: float = 2.0
    kafka_flush_timeout_seconds: float = 5.0
    kafka_poll_interval_seconds: float = 0.01

    # OpenTelemetry
    otel_enabled: bool = True
    otel_service_name: str = "events-service"

    otel_exporter_otlp_endpoint: str = "http://jaeger:4317"
    otel_exporter_otlp_insecure: bool = True

    @property
    def kafka_producer_config(self) -> dict[str, Any]:
        """Сформировать конфигурацию Kafka Producer."""
        return {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "client.id": self.kafka_client_id,
            "acks": self.kafka_acks,
            "enable.idempotence": self.kafka_enable_idempotence,
            "linger.ms": self.kafka_linger_ms,
            "compression.type": self.kafka_compression_type,
            "delivery.timeout.ms": self.kafka_delivery_timeout_ms,
        }


@lru_cache
def get_settings() -> Settings:
    """Получить закешированные настройки приложения."""
    return Settings()
