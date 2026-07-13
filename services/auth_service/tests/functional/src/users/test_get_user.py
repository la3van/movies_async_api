"""Функциональные тесты получения текущего пользователя."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.responses import USER_RESPONSE_FIELDS
from tests.functional.utils.helpers import (
    assert_has_fields,
    build_auth_headers,
)


@pytest.mark.asyncio
async def test_get_current_user(
    registered_user,
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет получение профиля текущего пользователя."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_has_fields(body, USER_RESPONSE_FIELDS)
        assert body['id'] == registered_user['id']
        assert body['login'] == registered_user['login']
        assert body['email'] == registered_user['email']


@pytest.mark.asyncio
async def test_get_current_user_from_cache(
    registered_user_tokens,
    make_get_request,
    delete_user_by_id,
) -> None:
    """Проверяет возврат профиля из Redis после удаления строки в БД."""
    headers = build_auth_headers(registered_user_tokens['access_token'])

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK

    await delete_user_by_id(first_body['id'])

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_current_user_without_token(make_get_request) -> None:
    """Проверяет запрет получения профиля без access-токена."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.parametrize(
    'authorization',
    [
        'Bearer invalid-token',
        'Basic abc',
        'Bearer',
    ],
)
@pytest.mark.asyncio
async def test_get_current_user_with_invalid_authorization(
    make_get_request,
    authorization,
) -> None:
    """Проверяет ошибочные Authorization-заголовки."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers={'Authorization': authorization},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail']


@pytest.mark.asyncio
async def test_get_current_inactive_user(
    registered_user_tokens,
    get_user_by_login,
    pg_execute,
    redis_client,
    make_get_request,
) -> None:
    """Проверяет запрет доступа для неактивного пользователя."""
    user = await get_user_by_login('test_user')

    assert user is not None

    await pg_execute(
        'UPDATE users SET is_active = false WHERE id = $1::uuid;',
        user['id'],
    )
    await redis_client.flushdb()

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=build_auth_headers(
            registered_user_tokens['access_token'],
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'User is inactive'
