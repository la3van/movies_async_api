"""Фикстуры HTTP-клиента функциональных тестов."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import aiohttp
import jwt
import pytest
import pytest_asyncio

from tests.functional.settings import test_settings


def build_access_token() -> str:
    """Создаёт access-токен пользователя с правом чтения контента."""
    issued_at = datetime.now(timezone.utc)

    return jwt.encode(
        {
            "sub": str(uuid4()),
            "type": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(hours=1)).timestamp()),
            "login": "functional-test-user",
            "roles": [],
            "permissions": ["content:read"],
            "is_superuser": False,
        },
        test_settings.jwt_secret_key,
        algorithm=test_settings.jwt_algorithm,
    )


@pytest_asyncio.fixture(name="http_session", scope="session")
async def http_session():
    """Создаёт HTTP-сессию на время тестовой сессии."""
    access_token = build_access_token()
    session = aiohttp.ClientSession(
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    yield session
    await session.close()


@pytest.fixture(name="make_get_request")
def make_get_request(http_session: aiohttp.ClientSession):
    """Возвращает функцию выполнения GET-запросов к тестируемому API."""

    async def inner(url: str, query_data: dict[str, Any] | None = None):
        """Выполняет GET-запрос с переданными query-параметрами."""
        url = f"{test_settings.service_url.rstrip('/')}/{url.lstrip('/')}"

        return await http_session.get(
            url,
            params=query_data,
        )

    return inner
