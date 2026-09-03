"""Интерфейс загрузчика документов в целевое хранилище."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from postgres_to_es.models import BaseDocument


class DocumentLoader(ABC):
    """Загружает документы в целевое хранилище."""

    @abstractmethod
    def create_index_if_not_exists(
        self,
        index_name: str,
        schema_filename: str,
    ) -> None:
        """Создаёт индекс, если он еще не существует."""
        # pragma: no cover

    @abstractmethod
    def bulk_load(
        self,
        index_name: str,
        documents: Sequence[BaseDocument],
    ) -> None:
        """Загружает последовательность документов в индекс."""
        # pragma: no cover
