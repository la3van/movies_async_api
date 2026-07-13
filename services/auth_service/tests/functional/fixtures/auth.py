"""Фикстуры аутентификации функциональных тестов."""
from http import HTTPStatus
from typing import Any

import pytest
import pytest_asyncio

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    get_login_data,
    get_register_data,
    get_second_register_data,
)
from tests.functional.test_data.permissions import (
    get_permission_create_data,
    get_second_permission_create_data,
)
from tests.functional.test_data.roles import get_role_create_data
from tests.functional.utils.helpers import build_auth_headers


@pytest_asyncio.fixture(name='registered_user_tokens')
async def registered_user_tokens(make_post_request) -> dict[str, Any]:
    """Регистрирует пользователя и возвращает пару токенов."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED

        return body


@pytest_asyncio.fixture(name='registered_user')
async def registered_user(
    registered_user_tokens: dict[str, Any],
    make_get_request,
) -> dict[str, Any]:
    """Регистрирует пользователя и возвращает его профиль."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=build_auth_headers(
            registered_user_tokens['access_token'],
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK

        return body


@pytest.fixture(name='access_token')
def access_token(registered_user_tokens: dict[str, Any]) -> str:
    """Возвращает access-token зарегестрированного пользователя."""
    return registered_user_tokens['access_token']


@pytest.fixture(name='refresh_token')
def refresh_token(registered_user_tokens: dict[str, Any]) -> str:
    """Возвращает refresh-token зарегестрированного пользователя."""
    return registered_user_tokens['refresh_token']


@pytest.fixture(name='auth_headers')
def auth_headers(access_token: str) -> dict[str, str]:
    """Возвращает Authorization headers обычного пользователя."""
    return build_auth_headers(access_token)


@pytest_asyncio.fixture(name='logged_in_user_tokens')
async def logged_in_user_tokens(
    registered_user_tokens: dict[str, Any],
    make_post_request,
) -> dict[str, Any]:
    """Логинит зарегестрированного пользователя и возвращает пару токенов."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK

        return body


@pytest_asyncio.fixture(name='second_registered_user_tokens')
async def second_registered_user_tokens(make_post_request) -> dict[str, Any]:
    """Регистрирует второго пользователя и возвращает пару токенов."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_second_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED

        return body


@pytest_asyncio.fixture(name='second_registered_user')
async def second_registered_user(
    second_registered_user_tokens: dict[str, Any],
    make_get_request,
) -> dict[str, Any]:
    """Регистрирует второго пользователя и возвращает его профиль."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=build_auth_headers(
            second_registered_user_tokens['access_token'],
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK

        return body


@pytest.fixture(name='second_auth_headers')
def second_auth_headers(
    second_registered_user_tokens: dict[str, Any],
) -> dict[str, str]:
    """Возвращает Authorization headers второго пользователя."""
    return build_auth_headers(
        second_registered_user_tokens['access_token'],
    )


@pytest_asyncio.fixture(name='superuser_tokens')
async def superuser_tokens(
    make_post_request,
    get_user_by_login,
    promote_user_to_superuser,
    redis_client,
) -> dict[str, Any]:
    """Создаёт суперпользователя и возвращает пару токенов."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_register_data(
            login='superuser',
            email='superuser@example.com',
            password='superuser_password',
            first_name='Super',
            last_name='User',
        ),
    )

    async with response:
        await response.json()

        assert response.status == HTTPStatus.CREATED

    user = await get_user_by_login('superuser')

    assert user is not None

    await promote_user_to_superuser(user['id'])

    await redis_client.flushdb()

    login_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(
            login='superuser',
            password='superuser_password',
        ),
    )

    async with login_response:
        login_body = await login_response.json()

        assert login_response.status == HTTPStatus.OK

        return login_body


@pytest.fixture(name='superuser_headers')
def superuser_headers(superuser_tokens: dict[str, Any]) -> dict[str, str]:
    """Возвращает Authorization headers суперпользователя."""
    return build_auth_headers(superuser_tokens['access_token'])


@pytest_asyncio.fixture(name='superuser')
async def superuser(
    superuser_headers: dict[str, str],
    make_get_request,
) -> dict[str, Any]:
    """Возвращает профиль суперпользователя."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['is_superuser'] is True

        return body


@pytest_asyncio.fixture(name='created_permission')
async def created_permission(
    superuser_headers: dict[str, str],
    make_post_request,
) -> dict[str, Any]:
    """Создаёт permission через API и возвращает его."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/',
        json_data=get_permission_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED

        return body


@pytest_asyncio.fixture(name='created_second_permission')
async def created_second_permission(
    superuser_headers: dict[str, str],
    make_post_request,
) -> dict[str, Any]:
    """Создаёт второй permission через API и возвращает его."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/',
        json_data=get_second_permission_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED

        return body


@pytest_asyncio.fixture(name='created_role')
async def created_role(
    superuser_headers: dict[str, str],
    created_permission: dict[str, Any],
    make_post_request,
) -> dict[str, Any]:
    """Создаёт роль через API и возвращает её."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(
            permission_ids=[created_permission['id']],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED

        return body


@pytest_asyncio.fixture(name='user_with_role')
async def user_with_role(
    registered_user: dict[str, Any],
    created_role: dict[str, Any],
    superuser_headers: dict[str, str],
    make_post_request,
) -> dict[str, Any]:
    """Назначает обычному пользователю роль и возвращает пользователя."""
    response = await make_post_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{registered_user["id"]}'
            f'/roles/{created_role["id"]}'
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK

        return body
