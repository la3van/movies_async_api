"""Функциональные тесты auth endpoints."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    VALID_USER_EMAIL,
    VALID_USER_LOGIN,
    get_duplicate_email_register_data,
    get_duplicate_login_register_data,
    get_invalid_email_register_data,
    get_invalid_refresh_data,
    get_login_data,
    get_logout_data,
    get_missing_user_login_data,
    get_refresh_data,
    get_register_data,
    get_short_password_register_data,
    get_wrong_password_login_data,
)
from tests.functional.utils.helpers import assert_token_pair_response


@pytest.mark.asyncio
async def test_register_user(
    make_post_request,
    get_user_by_login,
    get_login_history_by_login,
) -> None:
    """Проверяет успешную регистрацию пользователя."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert_token_pair_response(body)

    user = await get_user_by_login(VALID_USER_LOGIN)

    assert user is not None
    assert user['login'] == VALID_USER_LOGIN
    assert user['email'] == VALID_USER_EMAIL
    assert user['is_active'] is True
    assert user['is_superuser'] is False

    login_history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(login_history) == 1
    assert login_history[0]['is_successful'] is True
    assert login_history[0]['reason'] is None


@pytest.mark.asyncio
async def test_register_user_with_existing_login(
    registered_user,
    make_post_request,
) -> None:
    """Проверяет ошибку регистрации с уже существующим login."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_duplicate_login_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'User with this login already exists'


@pytest.mark.asyncio
async def test_register_user_with_existing_email(
    registered_user,
    make_post_request,
) -> None:
    """Проверяет ошибку регистрации с уже существующим email."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_duplicate_email_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'User with this email already exists'


@pytest.mark.asyncio
async def test_register_user_with_invalid_email(
    make_post_request,
) -> None:
    """Проверяет валидацию email при регистрации."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_invalid_email_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_register_user_with_short_password(
    make_post_request,
) -> None:
    """Проверяет валидацию короткого пароля при регистрации."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/register',
        json_data=get_short_password_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_login_user(
    registered_user,
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет успешный логин пользователя."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_token_pair_response(body)

    login_history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(login_history) == 2
    assert login_history[-1]['is_successful'] is True
    assert login_history[-1]['reason'] is None


@pytest.mark.asyncio
async def test_login_user_with_wrong_password(
    registered_user,
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет ошибку логина с неверным паролем."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_wrong_password_login_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid login or password'

    login_history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(login_history) == 2
    assert login_history[-1]['is_successful'] is False
    assert login_history[-1]['reason'] == 'Invalid password'


@pytest.mark.asyncio
async def test_login_missing_user(
    make_post_request,
    get_login_history_by_login,
) -> None:
    """Проверяет ошибку логина несуществующего пользователя."""
    login_data = get_missing_user_login_data()

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=login_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid login or password'

    login_history = await get_login_history_by_login(login_data['login'])

    assert len(login_history) == 1
    assert login_history[0]['user_id'] is None
    assert login_history[0]['is_successful'] is False
    assert login_history[0]['reason'] == 'User not found'


@pytest.mark.asyncio
async def test_refresh_tokens(
    registered_user,
    refresh_token,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет rotation refresh-токена."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_token_pair_response(body)
        assert body['refresh_token'] != refresh_token

    refresh_sessions = await get_refresh_sessions_by_user_id(
        registered_user['id'],
    )

    assert len(refresh_sessions) == 2
    assert (
        sum(session['revoked_at'] is not None
            for session in refresh_sessions) == 1
    )
    assert (
        sum(session['revoked_at'] is None
            for session in refresh_sessions) == 1
    )

    old_refresh_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with old_refresh_response:
        old_refresh_body = await old_refresh_response.json()

        assert old_refresh_response.status == HTTPStatus.UNAUTHORIZED
        assert old_refresh_body['detail'] == 'Refresh token has been revoked'


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(
    make_post_request,
) -> None:
    """Проверяет ошибку refresh с невалидным токеном."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_invalid_refresh_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_logout(
    registered_user,
    refresh_token,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет logout текущей refresh-сессии."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/logout',
        json_data=get_logout_data(refresh_token),
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    refresh_sessions = await get_refresh_sessions_by_user_id(
        registered_user['id'],
    )

    assert len(refresh_sessions) == 1
    assert refresh_sessions[0]['revoked_at'] is not None

    refresh_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with refresh_response:
        body = await refresh_response.json()

        assert refresh_response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Refresh token has been revoked'


@pytest.mark.asyncio
async def test_logout_with_invalid_token(
    make_post_request,
) -> None:
    """Проверяет ошибку logout с невалидным refresh-токеном."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/logout',
        json_data=get_invalid_refresh_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid refresh token'


@pytest.mark.asyncio
async def test_logout_others(
    registered_user,
    registered_user_tokens,
    logged_in_user_tokens,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет logout из остальных refresh-сессий."""
    first_refresh_token = registered_user_tokens['refresh_token']
    current_refresh_token = logged_in_user_tokens['refresh_token']

    response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/logout-others',
        json_data=get_logout_data(current_refresh_token),
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    refresh_sessions = await get_refresh_sessions_by_user_id(
        registered_user['id'],
    )

    assert len(refresh_sessions) == 2
    assert (
        sum(session['revoked_at'] is not None
            for session in refresh_sessions) == 1
    )
    assert (
        sum(session['revoked_at'] is None
            for session in refresh_sessions) == 1
    )

    old_session_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(first_refresh_token),
    )

    async with old_session_response:
        body = await old_session_response.json()

        assert old_session_response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Refresh token has been revoked'

    current_session_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(current_refresh_token),
    )

    async with current_session_response:
        body = await current_session_response.json()

        assert current_session_response.status == HTTPStatus.OK
        assert_token_pair_response(body)
