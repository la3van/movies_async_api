"""Общие фикстуры Redis."""

import pytest_asyncio
from redis.asyncio import Redis

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name="redis_client", scope="session")
async def redis_client():
    """Создаёт Redis-клиент на время тестовой сессии."""
    redis_client = Redis.from_url(
        test_settings.get_redis_url(),
        socket_connect_timeout=(test_settings.redis_socket_connect_timeout),
        socket_timeout=test_settings.redis_socket_timeout,
    )
    yield redis_client
    await redis_client.aclose()


@pytest_asyncio.fixture(name="redis_clear", autouse=True)
async def redis_clear(redis_client):
    """Очищает Redis до и после каждого теста."""
    await redis_client.flushdb()

    yield

    await redis_client.flushdb()
