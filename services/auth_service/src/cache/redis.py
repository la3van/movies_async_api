"""Реализация кеша приложения на основе Redis."""
import json
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis

from cache.base import Cache

ModelType = TypeVar('ModelType', bound=BaseModel)


class RedisCache(Cache):
    """Хранит сериализованные Pydantic-модели в Redis."""
    def __init__(self, redis: Redis) -> None:
        """Инициализирует кеш с готовым клиентом Redis."""
        self._redis = redis

    async def get_model(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> ModelType | None:
        """Возвращает одну десериализованную модель из Redis."""
        cached_data = await self._redis.get(key)

        if cached_data is None:
            return None

        return model_type.model_validate_json(cached_data)

    async def get_models(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> list[ModelType] | None:
        """Возвращает список десериализованных моделей из Redis."""
        cached_data = await self._redis.get(key)

        if cached_data is None:
            return None

        raw_models = json.loads(cached_data)

        return [
            model_type.model_validate(raw_model)
            for raw_model in raw_models
        ]

    async def set_model(
        self,
        key: str,
        value: BaseModel,
        ttl: int,
    ) -> None:
        """Сериализует и сохраняет одну модель в Redis."""
        await self._redis.set(
            name=key,
            value=value.model_dump_json(),
            ex=ttl,
        )

    async def set_models(
        self,
        key: str,
        values: Sequence[BaseModel],
        ttl: int,
    ) -> None:
        """Сериализует и сохраняет последовательность моделей в Redis."""
        serialized_values = [
            value.model_dump(mode='json')
            for value in values
        ]

        await self._redis.set(
            key,
            json.dumps(serialized_values),
            ex=ttl,
        )

    async def delete(self, key: str) -> None:
        """Удаляет значение из кеша."""
        await self._redis.delete(key)

    async def delete_many(self, keys: Sequence[str]) -> None:
        """Удаляет несколько значений из кеша."""
        if not keys:
            return

        await self._redis.delete(*keys)
