"""Фикстуры HTTP-клиента функциональных тестов."""
from typing import Any

import aiohttp
import pytest
import pytest_asyncio

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name='http_session', scope='session')
async def http_session():
    """Создаёт HTTP-сессию на время тестовой сессии."""
    timeout = aiohttp.ClientTimeout(
        total=test_settings.http_request_timeout,
    )

    session = aiohttp.ClientSession(timeout=timeout)
    yield session
    await session.close()


@pytest.fixture(name='make_get_request')
def make_get_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения GET-запросов к auth-service."""
    async def inner(
        url: str,
        query_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Выполняет GET-запрос."""
        return await http_session.get(
            build_url(url),
            params=query_data,
            headers=headers,
        )

    return inner


@pytest.fixture(name='make_post_request')
def make_post_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения POST-запросов к auth-service."""
    async def inner(
        url: str,
        json_data: dict[str, Any] | None = None,
        query_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Выполняет POST-запрос."""
        return await http_session.post(
            build_url(url),
            json=json_data,
            params=query_data,
            headers=headers,
        )

    return inner


@pytest.fixture(name='make_patch_request')
def make_patch_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения PATCH-запросов к auth-service."""
    async def inner(
        url: str,
        json_data: dict[str, Any] | None = None,
        query_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Выполняет PATCH-запрос."""
        return await http_session.patch(
            build_url(url),
            json=json_data,
            params=query_data,
            headers=headers,
        )

    return inner


@pytest.fixture(name='make_delete_request')
def make_delete_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения DELETE-запросов к auth-service."""
    async def inner(
        url: str,
        json_data: dict[str, Any] | None = None,
        query_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        """Выполняет DELETE-запрос."""
        return await http_session.delete(
            build_url(url),
            json=json_data,
            params=query_data,
            headers=headers,
        )

    return inner


def build_url(url: str) -> str:
    """Собирает полный URL до auth-service."""
    return f'{test_settings.service_url.rstrip("/")}/{url.lstrip("/")}'
