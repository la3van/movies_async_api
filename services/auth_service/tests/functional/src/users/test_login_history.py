"""Функциональные тесты истории входов пользователя."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    get_login_data,
    get_wrong_password_login_data,
)
from tests.functional.test_data.responses import LOGIN_HISTORY_RESPONSE_FIELDS
from tests.functional.utils.helpers import (
    assert_has_fields,
    build_auth_headers,
)


@pytest.mark.asyncio
async def test_get_login_history(
    registered_user,
    auth_headers,
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет получение истории входов."""
    login_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with login_response:
        assert login_response.status == HTTPStatus.OK

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert len(body) == 2
        assert_has_fields(body[0], LOGIN_HISTORY_RESPONSE_FIELDS)
        assert all(item['login'] == registered_user['login'] for item in body)


@pytest.mark.asyncio
async def test_get_login_history_with_pagination(
    auth_headers,
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет limit и offset истории входов."""
    for _ in range(2):
        login_response = await make_post_request(
            url=f'{test_settings.api_prefix}/auth/login',
            json_data=get_login_data(),
        )

        async with login_response:
            assert login_response.status == HTTPStatus.OK

    full_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with full_response:
        full_body = await full_response.json()

        assert full_response.status == HTTPStatus.OK
        assert len(full_body) == 3

    page_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 1, 'offset': 1},
    )

    async with page_response:
        page_body = await page_response.json()

        assert page_response.status == HTTPStatus.OK
        assert page_body == [full_body[1]]


@pytest.mark.asyncio
async def test_get_login_history_from_cache(
    registered_user_tokens,
    make_get_request,
    delete_login_history_by_user_id,
) -> None:
    """Проверяет возврат истории из Redis после удаления строк в БД."""
    headers = build_auth_headers(registered_user_tokens['access_token'])

    user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with user_response:
        user = await user_response.json()

        assert user_response.status == HTTPStatus.OK

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body) == 1

    await delete_login_history_by_user_id(user['id'])

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_successful_login_invalidates_history_cache(
    auth_headers,
    make_get_request,
    make_post_request,
) -> None:
    """Проверяет инвалидацию истории после успешного входа."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body) == 1

    login_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with login_response:
        assert login_response.status == HTTPStatus.OK

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert len(second_body) == 2
        assert second_body != first_body
        assert second_body[0]['is_successful'] is True


@pytest.mark.asyncio
async def test_failed_login_invalidates_history_cache(
    auth_headers,
    make_get_request,
    make_post_request,
) -> None:
    """Проверяет инвалидацию истории после неуспешного входа."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body) == 1

    login_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_wrong_password_login_data(),
    )

    async with login_response:
        assert login_response.status == HTTPStatus.UNAUTHORIZED

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert len(second_body) == 2
        assert second_body != first_body
        assert second_body[0]['is_successful'] is False
        assert second_body[0]['reason'] == 'Invalid password'


@pytest.mark.parametrize(
    'query_data',
    [
        {'limit': 0},
        {'limit': -1},
        {'limit': 201},
        {'limit': 'invalid'},
        {'offset': -1},
        {'offset': 'invalid'},
    ],
)
@pytest.mark.asyncio
async def test_get_login_history_with_invalid_query(
    auth_headers,
    make_get_request,
    query_data,
) -> None:
    """Проверяет валидацию пагинации истории входов."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_get_login_history_without_token(make_get_request) -> None:
    """Проверяет запрет получения истории без токена."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'
