"""Жизненный цикл асинхронного клиента Redis."""

from core.config import get_settings
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff
from redis.exceptions import ConnectionError, TimeoutError

redis: Redis | None = None


async def init_redis() -> None:
    """Создать общий пул Redis."""
    global redis
    settings = get_settings()
    redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        socket_connect_timeout=settings.redis_socket_connect_timeout,
        socket_timeout=settings.redis_socket_timeout,
        decode_responses=False,
        retry=Retry(
            backoff=ExponentialWithJitterBackoff(
                base=settings.redis_retry_backoff_base,
                cap=settings.redis_retry_backoff_cap,
            ),
            retries=settings.redis_max_retries,
            supported_errors=(ConnectionError, TimeoutError),
        ),
    )


async def close_redis() -> None:
    """Закрыть пул Redis."""
    global redis
    if redis is not None:
        await redis.aclose()
    redis = None


async def get_redis() -> Redis:
    """Вернуть инициализированный Redis."""
    if redis is None:
        raise RuntimeError("Redis is not initialized")
    return redis
