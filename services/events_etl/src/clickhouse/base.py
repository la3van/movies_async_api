"""Базовый интерфейс хранилища пользовательских событий."""

from typing import Protocol

from models.rows import ClickHouseEventRow


class EventStorage(Protocol):
    """Интерфейс хранилища пользовательских событий."""

    def insert_batch(
        self,
        rows: list[ClickHouseEventRow],
    ) -> None:
        """Сохранить пакет пользовательских событий."""
        # pragma: no cover

    def is_ready(self) -> bool:
        """Проверить доступность хранилища."""
        # pragma: no cover

    def close(self) -> None:
        """Корректно завершить работу с хранилищем."""
        # pragma: no cover
