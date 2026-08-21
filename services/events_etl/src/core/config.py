"""Настройки ETL-сервиса переноса пользовательских событий в ClickHouse."""
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки ETL-сервиса."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    project_name: str = "events-etl"

    # Kafka
    kafka_bootstrap_servers: str = (
        "kafka-0:9092,"
        "kafka-1:9092,"
        "kafka-2:9092"
    )

    kafka_topic: str = "user-events"
    kafka_group_id: str = "events-clickhouse-etl"
    kafka_client_id: str = "events-etl"

    kafka_dlq_topic: str = "user-events-dlq"
    kafka_dlq_client_id: str = "events-etl-dlq"
    kafka_dlq_delivery_timeout_ms: int = Field(
        default=5_000,
        gt=0,
    )
    kafka_dlq_flush_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
    )

    # Намеренно используем earliest. При обычном рестарте Consumer
    # продолжает с committed offsets; reset применяется только если
    # валидного offset у группы нет. Kafka служит источником восстановления
    # ClickHouse, а повторная обработка безопасна благодаря дедупликации
    # пользовательских событий по event_id.
    kafka_auto_offset_reset: Literal[
        "earliest",
        "latest",
        "error",
    ] = "earliest"

    kafka_batch_size: int = Field(
        default=500,
        gt=0,
    )

    kafka_poll_timeout_seconds: float = Field(
        default=1.0,
        gt=0,
    )

    kafka_enable_auto_commit: bool = False
    kafka_enable_auto_offset_store: bool = False

    kafka_retry_initial_delay_seconds: float = Field(
        default=1.0,
        gt=0,
    )

    kafka_retry_max_delay_seconds: float = Field(
        default=30.0,
        gt=0,
    )

    # ClickHouse
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = Field(
        default=8123,
        gt=0,
        le=65_535,
    )

    clickhouse_username: str = "events_etl"
    clickhouse_password: SecretStr

    clickhouse_database: str = "analytics"
    clickhouse_table: str = "user_events"

    clickhouse_connect_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
    )
    clickhouse_send_receive_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
    )

    clickhouse_max_retries: int = Field(
        default=0,
        ge=0,
    )
    clickhouse_retry_initial_delay_seconds: float = Field(
        default=1.0,
        gt=0,
    )
    clickhouse_retry_max_delay_seconds: float = Field(
        default=30.0,
        gt=0,
    )

    # Monitoring
    metrics_host: str = "0.0.0.0"
    metrics_port: int = Field(
        default=9100,
        gt=0,
        le=65_535,
    )

    @model_validator(mode="after")
    def validate_retry_settings(self) -> "Settings":
        """Проверить согласованность настроек повторных попыток."""
        if (
            self.clickhouse_retry_max_delay_seconds
            < self.clickhouse_retry_initial_delay_seconds
        ):
            raise ValueError(
                "CLICKHOUSE_RETRY_MAX_DELAY_SECONDS "
                "не может быть меньше "
                "CLICKHOUSE_RETRY_INITIAL_DELAY_SECONDS"
            )

        if (
            self.kafka_retry_max_delay_seconds
            < self.kafka_retry_initial_delay_seconds
        ):
            raise ValueError(
                "KAFKA_RETRY_MAX_DELAY_SECONDS "
                "не может быть меньше "
                "KAFKA_RETRY_INITIAL_DELAY_SECONDS"
            )

        return self

    @property
    def kafka_consumer_config(self) -> dict[str, Any]:
        """Сформировать конфигурацию Kafka Consumer."""
        return {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "group.id": self.kafka_group_id,
            "client.id": self.kafka_client_id,
            "auto.offset.reset": self.kafka_auto_offset_reset,
            "enable.auto.commit": self.kafka_enable_auto_commit,
            "enable.auto.offset.store": self.kafka_enable_auto_offset_store,
        }

    @property
    def kafka_dlq_producer_config(
        self,
    ) -> dict[str, Any]:
        """Сформировать конфигурацию Kafka DLQ Producer."""
        return {
            "bootstrap.servers": self.kafka_bootstrap_servers,
            "client.id": self.kafka_dlq_client_id,
            "acks": "all",
            "enable.idempotence": True,
            "delivery.timeout.ms": (
                self.kafka_dlq_delivery_timeout_ms
            ),
        }

    @property
    def clickhouse_table_name(self) -> str:
        """Получить полное имя целевой таблицы ClickHouse."""
        return f"{self.clickhouse_database}.{self.clickhouse_table}"

    @property
    def clickhouse_password_value(self) -> str:
        """Получить пароль ClickHouse для передачи клиенту."""
        return self.clickhouse_password.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    """Получить закешированные настройки ETL-сервиса."""
    return Settings()
