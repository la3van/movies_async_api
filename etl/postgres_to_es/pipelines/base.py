"""Базовый класс ETL-пайплайна."""
from abc import ABC, abstractmethod
from datetime import datetime

from psycopg2.extensions import connection as PgConnection

from postgres_to_es.interfaces import DocumentLoader
from postgres_to_es.models import ChangedRecord
from postgres_to_es.state import State, StateData

DEFAULT_MODIFIED = '0001-01-01T00:00:00+00:00'
DEFAULT_ID = '00000000-0000-0000-0000-000000000000'


class BasePipeline(ABC):
    """Содержит общую логику ETL-пайплайнов."""
    def __init__(
        self,
        loader: DocumentLoader,
        state: State,
        index_name: str,
        schema_filename: str,
        batch_size: int,
    ) -> None:
        """Инициализирует общие зависимости пайплайна."""
        if batch_size <= 0:
            raise ValueError(
                'Размер пакета ETL должен быть положительным.',
            )

        self._loader = loader
        self._state = state
        self._index_name = index_name
        self._schema_filename = schema_filename
        self._batch_size = batch_size

    def prepare(self) -> None:
        """Подготавливает целевой индекс пайплайна."""
        self._loader.create_index_if_not_exists(
            index_name=self._index_name,
            schema_filename=self._schema_filename,
        )

    @abstractmethod
    def run_iteration(
        self,
        connection: PgConnection,
    ) -> bool:
        """Выполняет одну итерацию пайплайна."""
        pass  # pragma: no cover

    def _get_cursor(
        self,
        prefix: str,
    ) -> tuple[str, str]:
        """Получает курсор таблицы из состояния ETL."""
        modified = self._get_state_string(
            key=f'{prefix}_modified',
            default=DEFAULT_MODIFIED,
        )
        record_id = self._get_state_string(
            key=f'{prefix}_id',
            default=DEFAULT_ID,
        )

        return modified, record_id

    def _get_cursor_update(
        self,
        prefix: str,
        records: list[ChangedRecord],
    ) -> StateData:
        """Формирует новое состояние курсора."""
        if not records:
            return {}

        last_record = records[-1]

        return {
            f'{prefix}_modified': self._serialize_modified(
                last_record.modified,
            ),
            f'{prefix}_id': last_record.id,
        }

    def _get_state_string(
        self,
        key: str,
        default: str,
    ) -> str:
        """Получает строковое значение состояния."""
        value = self._state.get_state(key)

        if value is None:
            return default

        if not isinstance(value, str):
            raise ValueError(
                f'Значение состояния {key!r} должно быть строкой.',
            )

        return value

    @staticmethod
    def _serialize_modified(
        value: datetime | str,
    ) -> str:
        """Сериализует дату изменения для Redis."""
        if isinstance(value, datetime):
            return value.isoformat()

        return value
