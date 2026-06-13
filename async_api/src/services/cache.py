"""Общие функции для работы сервисов с Redis-кешем."""
import json
from collections.abc import Sequence
from typing import TypeVar, Optional

from pydantic import BaseModel
from redis.asyncio import Redis

ModelType = TypeVar('ModelType', bound=BaseModel)


async def get_model_from_cache(
    redis: Redis,
    key: str,
    model: type[ModelType],
) -> Optional[ModelType]:
    """Получает одну Pydantic-модель из Redis."""
    data = await redis.get(key)

    if data is None:
        return None

    return model.model_validate_json(data)


async def get_models_from_cache(
    redis: Redis,
    key: str,
    model: type[ModelType],
) -> Optional[list[ModelType]]:
    """Получает список Pydantic-моделей из Redis."""
    data = await redis.get(key)

    if data is None:
        return None

    raw_models = json.loads(data)

    return [
        model.model_validate(raw_model)
        for raw_model in raw_models
    ]


async def put_model_to_cache(
    redis: Redis,
    key: str,
    value: BaseModel,
    ttl: int,
) -> None:
    """Сохраняет одну Pydantic-модель в Redis."""
    await redis.set(
        key,
        value.model_dump_json(),
        ex=ttl,
    )


async def put_models_to_cache(
    redis: Redis,
    key: str,
    values: Sequence[BaseModel],
    ttl: int,
) -> None:
    """Сохраняет спсиок Pydantic-моделей в Redis."""
    serialized_values = [
        value.model_dump(mode='json')
        for value in values
    ]

    await redis.set(
        key,
        json.dumps(serialized_values),
        ex=ttl,
    )
