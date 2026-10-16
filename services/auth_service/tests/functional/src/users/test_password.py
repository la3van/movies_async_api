"""Функциональные тесты смены пароля."""

import json
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    VALID_USER_LOGIN,
    VALID_USER_PASSWORD,
    get_login_data,
    get_refresh_data,
)
from tests.functional.test_data.users import (
    NEW_PASSWORD,
    get_change_password_data,
    get_wrong_old_password_data,
)


@pytest.mark.asyncio
async def test_change_password(
    auth_headers,
    refresh_token,
    make_patch_request,
    make_post_request,
) -> None:
    """Проверяет смену пароля и отзыв refresh-сессий."""
    response = await make_patch_request(
        url=f"{test_settings.api_prefix}/users/me/password",
        json_data=get_change_password_data(
            old_password=VALID_USER_PASSWORD,
        ),
        headers=auth_headers,
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    old_password_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/login",
        json_data=get_login_data(
            login=VALID_USER_LOGIN,
            password=VALID_USER_PASSWORD,
        ),
    )

    async with old_password_response:
        body = await old_password_response.json()

        assert old_password_response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Invalid login or password"

    new_password_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/login",
        json_data=get_login_data(
            login=VALID_USER_LOGIN,
            password=NEW_PASSWORD,
        ),
    )

    async with new_password_response:
        body = await new_password_response.json()

        assert new_password_response.status == HTTPStatus.OK
        assert body["access_token"]
        assert body["refresh_token"]

    refresh_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/refresh",
        json_data=get_refresh_data(refresh_token),
    )

    async with refresh_response:
        body = await refresh_response.json()

        assert refresh_response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Refresh token has been revoked"


@pytest.mark.asyncio
async def test_change_password_invalidates_user_cache(
    registered_user,
    auth_headers,
    redis_exists,
    redis_client,
    make_get_request,
    make_patch_request,
) -> None:
    """Проверяет удаление кеша профиля после смены пароля."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/users/me",
        headers=auth_headers,
    )

    async with response:
        assert response.status == HTTPStatus.OK

    cache_key = f"user:profile:{registered_user['id']}"
    await redis_client.set(
        cache_key,
        json.dumps(registered_user),
        ex=60,
    )
    assert await redis_exists(cache_key) is True

    password_response = await make_patch_request(
        url=f"{test_settings.api_prefix}/users/me/password",
        json_data=get_change_password_data(
            old_password=VALID_USER_PASSWORD,
        ),
        headers=auth_headers,
    )

    async with password_response:
        assert password_response.status == HTTPStatus.NO_CONTENT

    assert await redis_exists(cache_key) is False


@pytest.mark.asyncio
async def test_change_password_with_wrong_old_password(
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет смену пароля с неверным старым паролем."""
    response = await make_patch_request(
        url=f"{test_settings.api_prefix}/users/me/password",
        json_data=get_wrong_old_password_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Invalid old password"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"new_password": NEW_PASSWORD},
        {"old_password": VALID_USER_PASSWORD},
        {"old_password": "short", "new_password": NEW_PASSWORD},
        {"old_password": VALID_USER_PASSWORD, "new_password": "short"},
        {"old_password": "x" * 129, "new_password": NEW_PASSWORD},
        {"old_password": VALID_USER_PASSWORD, "new_password": "x" * 129},
        {"old_password": None, "new_password": NEW_PASSWORD},
        {"old_password": VALID_USER_PASSWORD, "new_password": None},
        {"old_password": 123, "new_password": NEW_PASSWORD},
    ],
)
@pytest.mark.asyncio
async def test_change_password_with_invalid_payload(
    auth_headers,
    make_patch_request,
    payload,
) -> None:
    """Проверяет валидацию параметров смены пароля."""
    response = await make_patch_request(
        url=f"{test_settings.api_prefix}/users/me/password",
        json_data=payload,
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]


@pytest.mark.asyncio
async def test_change_password_without_token(make_patch_request) -> None:
    """Проверяет запрет смены пароля без токена."""
    response = await make_patch_request(
        url=f"{test_settings.api_prefix}/users/me/password",
        json_data=get_change_password_data(
            old_password=VALID_USER_PASSWORD,
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Not authenticated"
