import json
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel
from redis.asyncio import Redis

from cache.base import Cache

ModelType = TypeVar('ModelType', bound=BaseModel)


class RedisCache(Cache):
    def __init__(self, redis: Redis):
        self._redis = redis

    async def get_model(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> ModelType | None:
        cached_data = await self._redis.get(key)

        if cached_data is None:
            return None

        return model_type.model_validate_json(cached_data)

    async def get_models(
        self,
        key: str,
        model_type: type[ModelType],
    ) -> list[ModelType] | None:
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
        serialized_values = [
            value.model_dump(mode='json')
            for value in values
        ]

        await self._redis.set(
            key,
            json.dumps(serialized_values),
            ex=ttl,
        )
