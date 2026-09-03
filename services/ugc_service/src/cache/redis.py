"""Реализация кеша поверх Redis."""

from cache.base import Cache
from redis.asyncio import Redis


class RedisCache(Cache):
    """Кеш строковых значений в Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> bytes | None:
        value = await self._redis.get(key)
        return value if isinstance(value, bytes) else None

    async def set(self, key: str, value: bytes, ttl: int) -> None:
        await self._redis.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)
