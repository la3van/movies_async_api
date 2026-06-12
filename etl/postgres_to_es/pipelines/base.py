"""Базовый класс ETL-пайплайна."""
import abc
from datetime import datetime
from typing import Any

from postgres_to_es.models import ChangedRecord
from postgres_to_es.state import State, StateData

DEFAULT_MODIFIED = '0001-01-01T00:00:00+00:00'
DEFAULT_ID = '00000000-0000-0000-0000-000000000000'


class BasePipeline(abc.ABC):
    """Базовый класс для пайплайнов загрузки данных в Elasticsearch."""
    def __init__(
        self,
        postgres: Any,
        elasticsearch: Any,
        state: State,
        settings: Any,
    ):
        """Инициализирует зависимости пайплайна."""
        self.postgres = postgres
        self.elasticsearch = elasticsearch
        self.state = state
        self.settings = settings

    @abc.abstractmethod
    def prepare(self) -> None:
        """Подготавливает ресурсы пайплайна перед запуском."""

    @abc.abstractmethod
    def run_iteration(self, connection: Any) -> bool:
        """Выполняет одну итерацию пайплайна."""

    def _get_state(self, key: str) -> Any:
        """Получает значение состояния с дефолтным значением."""
        if key.endswith('_modified'):
            return self.state.get_state(key) or DEFAULT_MODIFIED

        if key.endswith('_id'):
            return self.state.get_state(key) or DEFAULT_ID

        return self.state.get_state(key)

    def _get_cursor_update(
        self,
        prefix: str,
        records: list[ChangedRecord],
    ) -> StateData:
        """Формирует обновление курсора состояния."""
        if not records:
            return {}

        last_record = records[-1]

        return {
            f'{prefix}_modified': self._serialize_modified(
                last_record.modified,
            ),
            f'{prefix}_id': last_record.id,
        }

    @staticmethod
    def _serialize_modified(value: datetime | str) -> str:
        """Сериализует дату изменения для хранения в состоянии."""
        if isinstance(value, datetime):
            return value.isoformat()

        return value
