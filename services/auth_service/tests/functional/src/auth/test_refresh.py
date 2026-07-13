"""Функциональные тесты обновления пары токенов."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    get_invalid_refresh_data,
    get_refresh_data,
)
from tests.functional.utils.helpers import assert_token_pair_response


@pytest.mark.asyncio
async def test_refresh_tokens(
    registered_user,
    refresh_token,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет ротацию refresh-токена."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
        headers={'User-Agent': 'auth-tests/refresh'},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_token_pair_response(body)
        assert body['refresh_token'] != refresh_token

    sessions = await get_refresh_sessions_by_user_id(registered_user['id'])

    assert len(sessions) == 2
    assert sum(item['revoked_at'] is not None for item in sessions) == 1
    assert sum(item['revoked_at'] is None for item in sessions) == 1
    assert sessions[-1]['user_agent'] == 'auth-tests/refresh'


@pytest.mark.asyncio
async def test_refresh_revokes_old_token(
    refresh_token,
    make_post_request,
) -> None:
    """Проверяет невозможность повторно использовать старый токен."""
    first_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with first_response:
        assert first_response.status == HTTPStatus.OK

    second_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with second_response:
        body = await second_response.json()

        assert second_response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Refresh token has been revoked'


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(make_post_request) -> None:
    """Проверяет неизвестный refresh-токен."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_invalid_refresh_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_refresh_with_expired_token(
    registered_user,
    refresh_token,
    pg_execute,
    make_post_request,
) -> None:
    """Проверяет истёкшую refresh-сессию."""
    await pg_execute(
        """
        UPDATE refresh_sessions
        SET expires_at = NOW() - INTERVAL '1 day'
        WHERE user_id = $1::uuid;
        """,
        registered_user['id'],
    )

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Refresh token has expired'


@pytest.mark.asyncio
async def test_refresh_for_inactive_user(
    registered_user,
    refresh_token,
    pg_execute,
    make_post_request,
) -> None:
    """Проверяет refresh для неактивного пользователя."""
    await pg_execute(
        'UPDATE users SET is_active = false WHERE id = $1::uuid;',
        registered_user['id'],
    )

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid refresh token'


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {},
        {'refresh_token': None},
        {'refresh_token': 123},
        {'token': 'wrong-field'},
    ],
)
@pytest.mark.asyncio
async def test_refresh_with_invalid_payload(
    make_post_request,
    payload,
) -> None:
    """Проверяет валидацию тела refresh-запроса."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_refresh_with_empty_token(make_post_request) -> None:
    """Проверяет пустой, но прошедший валидацию refresh-токен."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data={'refresh_token': ''},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid refresh token'
