"""Модуль зависимостей относительно redis'а."""
from typing import Optional

from redis.asyncio import Redis

from core.config import get_settings

redis: Optional[Redis] = None


async def init_redis() -> None:
    """Инициализирует клиент Redis."""
    global redis

    settings = get_settings()

    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
        decode_responses=False,
    )


async def close_redis() -> None:
    """Закрывает соединение с Redis."""
    global redis

    if redis is not None:
        await redis.close()
        redis = None


async def get_redis() -> Redis:
    """Возвращает клиент Redis для dependency injection."""
    if redis is None:
        raise RuntimeError('Redis client is not initialized')

    return redis
