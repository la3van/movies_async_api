"""Функциональные тесты входа пользователя."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    VALID_USER_LOGIN,
    get_login_data,
    get_missing_user_login_data,
    get_wrong_password_login_data,
)
from tests.functional.utils.helpers import assert_token_pair_response


@pytest.mark.asyncio
async def test_login_user(
    registered_user,
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет успешный вход и запись истории входа."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
        headers={'User-Agent': 'auth-tests/login'},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_token_pair_response(body)

    history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(history) == 2
    assert history[-1]['is_successful'] is True
    assert history[-1]['reason'] is None
    assert history[-1]['user_agent'] == 'auth-tests/login'
    assert history[-1]['ip_address'] is not None


@pytest.mark.asyncio
async def test_login_user_with_wrong_password(
    registered_user,
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет вход с неверным паролем и историю ошибки."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_wrong_password_login_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid login or password'

    history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(history) == 2
    assert history[-1]['is_successful'] is False
    assert history[-1]['reason'] == 'Invalid password'


@pytest.mark.asyncio
async def test_login_missing_user(
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет вход несуществующего пользователя."""
    payload = get_missing_user_login_data()

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid login or password'

    history = await get_login_history_by_login(payload['login'])

    assert len(history) == 1
    assert history[0]['user_id'] is None
    assert history[0]['is_successful'] is False
    assert history[0]['reason'] == 'User not found'


@pytest.mark.asyncio
async def test_login_inactive_user(
    registered_user,
    pg_execute,
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет запрет входа для неактивного пользователя."""
    await pg_execute(
        'UPDATE users SET is_active = false WHERE id = $1::uuid;',
        registered_user['id'],
    )

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'User is inactive'

    history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(history) == 2
    assert history[-1]['is_successful'] is False
    assert history[-1]['reason'] == 'User is inactive'


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {},
        {'password': 'password123'},
        {'login': VALID_USER_LOGIN},
        {'login': '', 'password': 'password123'},
        {'login': 'x' * 256, 'password': 'password123'},
        {'login': None, 'password': 'password123'},
        {'login': 123, 'password': 'password123'},
        {'login': VALID_USER_LOGIN, 'password': ''},
        {'login': VALID_USER_LOGIN, 'password': 'x' * 129},
        {'login': VALID_USER_LOGIN, 'password': None},
        {'login': VALID_USER_LOGIN, 'password': 123},
    ],
)
@pytest.mark.asyncio
async def test_login_with_invalid_payload(
    make_post_request,
    payload,
) -> None:
    """Проверяет валидацию тела запроса входа."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']
