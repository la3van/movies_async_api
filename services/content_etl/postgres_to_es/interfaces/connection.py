"""Интерфейс провайдера соединений с источником данных."""

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from psycopg2.extensions import connection as PgConnection


class ConnectionProvider(ABC):
    """Предоставляет соединение с PostgreSQL."""

    @abstractmethod
    def connection(
        self,
    ) -> AbstractContextManager[PgConnection]:
        """Возвращает контекстный менеджер PostgreSQL-соединения."""
        # pragma: no cover
