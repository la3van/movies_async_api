"""Реализация хранилища состояния ETL в Redis."""

import json
from typing import cast

from redis import Redis
from redis.exceptions import (
    ConnectionError as RedisConnectionError,
    TimeoutError as RedisTimeoutError,
)

from postgres_to_es.backoff import retryable
from postgres_to_es.interfaces import RetryExecutor
from postgres_to_es.state.base import StateData, StateStorage


class RedisStateStorage(StateStorage):
    """Хранит состояние одного ETL-пайплайна в Redis."""
    def __init__(
        self,
        redis_adapter: Redis,
        state_key: str,
        retry_executor: RetryExecutor,
    ) -> None:
        """Инициализирует Redis-хранилище состояния."""
        self._redis_adapter = redis_adapter
        self._state_key = state_key
        self._retry_executor = retry_executor

    @retryable(
        exceptions=(
            RedisConnectionError,
            RedisTimeoutError,
        ),
    )
    def save_state(self, state: StateData) -> None:
        """Сохраняет состояние ETL в Redis."""
        serialized_state = json.dumps(
            state,
            ensure_ascii=False,
        )

        self._redis_adapter.set(
            self._state_key,
            serialized_state,
        )

    @retryable(
        exceptions=(
            RedisConnectionError,
            RedisTimeoutError,
        ),
    )
    def retrieve_state(self) -> StateData:
        """Получает состояние ETL из Redis."""
        serialized_state = self._redis_adapter.get(
            self._state_key,
        )

        if serialized_state is None:
            return {}

        serialized_state = cast(
            str | bytes | bytearray,
            serialized_state,
        )

        state = json.loads(serialized_state)

        if not isinstance(state, dict):
            raise ValueError(
                'Состояние ETL в Redis должно быть JSON-объектом.',
            )

        return cast(StateData, state)
