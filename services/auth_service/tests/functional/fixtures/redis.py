"""Фикстуры Redis функциональных тестов."""

import pytest
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
        decode_responses=True,
    )

    yield redis_client

    await redis_client.aclose()


@pytest_asyncio.fixture(name="redis_clear", autouse=True)
async def redic_clear(redis_client: Redis):
    """Очищает Redis до и после каждого теста."""
    await redis_client.flushdb()

    yield

    await redis_client.flushdb()


@pytest.fixture(name="redis_get")
def redis_get(redis_client: Redis):
    """Возвращает функцию получения значения из Redis."""

    async def inner(key: str) -> str | None:
        """Возвращает значение Redis-ключа."""
        return await redis_client.get(key)

    return inner


@pytest.fixture(name="redis_exists")
def redis_exists(redis_client: Redis):
    """Возвращает функцию проверки существования Redis-ключа."""

    async def inner(key: str) -> bool:
        """Проверяет, существует ли Redis-ключ."""
        return bool(await redis_client.exists(key))

    return inner


@pytest.fixture(name="redis_keys")
def redis_keys(redis_client: Redis):
    """Возвращает функцию поиска Redis-ключей по pattern."""

    async def inner(pattern: str) -> list[str]:
        """Возвращает Redis-ключи по pattern."""
        return await redis_client.keys(pattern)

    return inner
