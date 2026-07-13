"""Функциональные тесты обновления профиля пользователя."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import VALID_USER_LOGIN
from tests.functional.test_data.responses import USER_RESPONSE_FIELDS
from tests.functional.test_data.users import (
    UPDATED_FIRST_NAME,
    UPDATED_LAST_NAME,
    get_full_update_profile_data,
    get_update_profile_data,
)
from tests.functional.utils.helpers import assert_has_fields


@pytest.mark.asyncio
async def test_update_current_user(
    registered_user,
    auth_headers,
    make_get_request,
    make_patch_request,
    get_user_by_login,
) -> None:
    """Проверяет полное обновление профиля и инвалидацию кеша."""
    cached_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with cached_response:
        cached_body = await cached_response.json()

        assert cached_response.status == HTTPStatus.OK

    update_response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_full_update_profile_data(),
        headers=auth_headers,
    )

    async with update_response:
        updated_body = await update_response.json()

        assert update_response.status == HTTPStatus.OK
        assert_has_fields(updated_body, USER_RESPONSE_FIELDS)
        assert updated_body['first_name'] == UPDATED_FIRST_NAME
        assert updated_body['last_name'] == UPDATED_LAST_NAME
        assert updated_body != cached_body

    user = await get_user_by_login(VALID_USER_LOGIN)

    assert user is not None
    assert user['first_name'] == UPDATED_FIRST_NAME
    assert user['last_name'] == UPDATED_LAST_NAME

    fresh_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with fresh_response:
        fresh_body = await fresh_response.json()

        assert fresh_response.status == HTTPStatus.OK
        assert fresh_body == updated_body


@pytest.mark.asyncio
async def test_update_only_first_name(
    registered_user,
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет PATCH только одного поля профиля."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_update_profile_data(first_name='OnlyFirstName'),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['first_name'] == 'OnlyFirstName'
        assert body['last_name'] == registered_user['last_name']


@pytest.mark.asyncio
async def test_update_user_clears_last_name(
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет явную очистку nullable-поля через null."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_update_profile_data(last_name=None),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['last_name'] is None


@pytest.mark.asyncio
async def test_update_user_with_empty_payload(
    registered_user,
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет допустимый пустой PATCH без изменения профиля."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_update_profile_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['first_name'] == registered_user['first_name']
        assert body['last_name'] == registered_user['last_name']


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {'first_name': 'x' * 256},
        {'last_name': 'x' * 256},
        {'first_name': 123},
        {'last_name': []},
    ],
)
@pytest.mark.asyncio
async def test_update_user_with_invalid_payload(
    auth_headers,
    make_patch_request,
    payload,
) -> None:
    """Проверяет валидацию PATCH-параметров профиля."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=payload,
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_update_user_without_token(make_patch_request) -> None:
    """Проверяет запрет обновления профиля без токена."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_full_update_profile_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'
