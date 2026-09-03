"""Менеджер состояния ETL-пайплайна."""

from typing import Any

from postgres_to_es.state.base import StateData, StateStorage


class State:
    """Управляет состоянием одного ETL-пайплайна."""

    def __init__(self, storage: StateStorage) -> None:
        """Загружает состояние из переданного хранилища."""
        self._storage = storage
        self._state = dict(storage.retrieve_state())

    def set_state(self, key: str, value: Any) -> None:
        """Сохраняет одно значение состояния."""
        new_state = dict(self._state)
        new_state[key] = value

        self._storage.save_state(new_state)
        self._state = new_state

    def set_states(self, values: StateData) -> None:
        """Сохраняет несколько значений состояния."""
        if not values:
            return

        new_state = dict(self._state)
        new_state.update(values)

        self._storage.save_state(new_state)
        self._state = new_state

    def get_state(self, key: str) -> Any:
        """Получает значение состояния по ключу."""
        return self._state.get(key)
