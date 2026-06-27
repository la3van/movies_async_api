"""Базовые типы и интерфейсы хранения состояния ETL."""
from abc import ABC, abstractmethod
from typing import Any, TypeAlias

StateData: TypeAlias = dict[str, Any]


class StateStorage(ABC):
    """Абстрактное хранилище состояния ETL."""
    @abstractmethod
    def save_state(self, state: StateData) -> None:
        """Сохраняет состояние ETL."""
        pass  # pragma: no cover

    @abstractmethod
    def retrieve_state(self) -> StateData:
        """Получает сохраненное состояние ETL."""
        pass  # pragma: no cover
