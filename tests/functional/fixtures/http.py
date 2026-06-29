"""Фикстуры HTTP-клиента функциональных тестов."""
from typing import Any

import aiohttp
import pytest
import pytest_asyncio

from tests.functional.settings import test_settings


@pytest_asyncio.fixture(name='http_session', scope='session')
async def http_session():
    """Создаёт HTTP-сессию на время тестовой сессии."""
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture(name='make_get_request')
def make_get_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения GET-запросов к тестируемому API."""
    async def inner(
        url: str,
        query_data: dict[str, Any] | None = None
    ):
        """Выполняет GET-запрос с переданными query-параметрами."""
        url = (
            f'{test_settings.service_url.rstrip("/")}/'
            f'{url.lstrip("/")}'
        )

        return await http_session.get(
            url,
            params=query_data,
        )

    return inner
