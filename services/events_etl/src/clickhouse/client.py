"""Запись пользовательских событий в ClickHouse."""

import logging
from typing import Final

import clickhouse_connect
from clickhouse.exceptions import (
    ClickHouseInsertError,
    ClickHouseStorageClosed,
)
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import ClickHouseError
from core.config import Settings
from models.rows import ClickHouseEventRow

logger = logging.getLogger(__name__)


CLICKHOUSE_COLUMNS: Final[tuple[str, ...]] = (
    "schema_version",
    "event_id",
    "event_type",
    "session_id",
    "user_id",
    "occurred_at",
    "received_at",
    "request_id",
    "page",
    "entity_type",
    "entity_id",
    "playback_id",
    "element_type",
    "element_id",
    "target_url",
    "referrer",
    "position_seconds",
    "duration_seconds",
    "from_quality",
    "to_quality",
    "genre_id",
    "sort",
    "search_query",
    "payload_json",
    "kafka_topic",
    "kafka_partition",
    "kafka_offset",
    "ingested_at",
)


class ClickHouseEventStorage:
    """Хранилище пользовательских событий в ClickHouse."""

    def __init__(
        self,
        settings: Settings,
        client: Client | None = None,
    ) -> None:
        """Создать клиент ClickHouse."""
        self._settings = settings
        self._closed = False

        self._client = client or clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_username,
            password=(settings.clickhouse_password_value),
            database=settings.clickhouse_database,
            connect_timeout=int(settings.clickhouse_connect_timeout_seconds),
            send_receive_timeout=int(
                settings.clickhouse_send_receive_timeout_seconds
            ),
        )

    def insert_batch(
        self,
        rows: list[ClickHouseEventRow],
    ) -> None:
        """Записать пакет пользовательских событий в ClickHouse."""
        self._ensure_open()

        if not rows:
            return

        data = [self._row_to_values(row) for row in rows]

        try:
            self._client.insert(
                table=self._settings.clickhouse_table_name,
                data=data,
                column_names=list(CLICKHOUSE_COLUMNS),
            )
        except ClickHouseError as exc:
            raise ClickHouseInsertError(
                "Не удалось записать пакет событий в ClickHouse"
            ) from exc

        logger.info(
            "Пакет событий записан в ClickHouse: table=%s rows=%s",
            self._settings.clickhouse_table_name,
            len(rows),
        )

    def is_ready(self) -> bool:
        """Проверить доступность ClickHouse."""
        if self._closed:
            return False

        try:
            result = self._client.query("SELECT 1")
        except ClickHouseError:
            logger.exception(
                "Не удалось выполнить проверочный запрос ClickHouse"
            )
            return False

        first_row = result.first_row
        return first_row is not None and first_row[0] == 1

    def close(self) -> None:
        """Корректно завершить работу клиента ClickHouse."""
        if self._closed:
            return

        self._closed = True

        try:
            self._client.close()
        except Exception:
            logger.exception("Ошибка при закрытии клиента ClickHouse")
        else:
            logger.info("Клиент ClickHouse успешно закрыт")

    def _ensure_open(self) -> None:
        """Проверить, что клиент ClickHouse не закрыт."""
        if self._closed:
            raise ClickHouseStorageClosed(
                "Клиент ClickHouse уже завершил работу"
            )

    @staticmethod
    def _row_to_values(
        row: ClickHouseEventRow,
    ) -> list:
        """Преобразовать модель строки в порядок колонок ClickHouse."""
        return [getattr(row, column) for column in CLICKHOUSE_COLUMNS]
