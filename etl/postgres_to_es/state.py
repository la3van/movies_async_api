"""Классы для хранения и управления состоянием ETL."""

import abc
import json
from typing import Any, cast

from redis import Redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

from postgres_to_es.backoff import backoff


StateData = dict[str, Any]
DEFAULT_STATE_KEY = 'data'


class BaseStorage(abc.ABC):
    """Абстрактное хранилище состояния ETL."""

    @abc.abstractmethod
    def save_state(self, state: StateData) -> None:
        """Сохраняет состояние в хранилище."""

    @abc.abstractmethod
    def retrieve_state(self) -> StateData:
        """Получает состояние из хранилища."""


class RedisStorage(BaseStorage):
    """Хранилище состояния ETL в Redis."""

    def __init__(
        self,
        redis_adapter: Redis,
        state_key: str = DEFAULT_STATE_KEY,
    ) -> None:
        """Инициализирует хранилище состояния в Redis."""
        self.redis_adapter = redis_adapter
        self.state_key = state_key

    @backoff(exceptions=(RedisConnectionError, RedisTimeoutError))
    def save_state(self, state: StateData) -> None:
        """Сохраняет состояние ETL в Redis."""
        json_state = json.dumps(state)
        self.redis_adapter.set(self.state_key, json_state)

    @backoff(exceptions=(RedisConnectionError, RedisTimeoutError))
    def retrieve_state(self) -> StateData:
        """Получает состояние ETL из Redis."""
        json_state = self.redis_adapter.get(self.state_key)

        if json_state is None:
            return {}

        json_state = cast(str | bytes | bytearray, json_state)

        state = json.loads(json_state)
        if not isinstance(state, dict):
            raise ValueError('Состояние ETL в Redis должно быть JSON-объектом')

        return state


class State:
    """Класс для работы с состоянием ETL."""

    def __init__(self, storage: BaseStorage) -> None:
        """Инициализирует менеджер состояния ETL."""
        self.storage = storage
        self.state = self.storage.retrieve_state()

    def set_state(self, key: str, value: Any) -> None:
        """Сохраняет новое значение состояния по ключу."""
        self.state[key] = value
        self.storage.save_state(self.state)

    def set_states(self, values: StateData) -> None:
        """Сохраняет несколько значений состояния за один раз."""
        self.state.update(values)
        self.storage.save_state(self.state)

    def get_state(self, key: str) -> Any:
        """Получает значение состояния по ключу."""
        return self.state.get(key)
