"""Функциональные тесты завершения refresh-сессий."""

from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    get_invalid_refresh_data,
    get_logout_data,
    get_refresh_data,
)
from tests.functional.utils.helpers import assert_token_pair_response


@pytest.mark.asyncio
async def test_logout(
    registered_user,
    refresh_token,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет отзыв текущей refresh-сессии."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/logout",
        json_data=get_logout_data(refresh_token),
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    sessions = await get_refresh_sessions_by_user_id(registered_user["id"])

    assert len(sessions) == 1
    assert sessions[0]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_logout_token_cannot_be_reused(
    refresh_token,
    make_post_request,
) -> None:
    """Проверяет невозможность повторно использовать отозванный токен."""
    logout_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/logout",
        json_data=get_logout_data(refresh_token),
    )

    async with logout_response:
        assert logout_response.status == HTTPStatus.NO_CONTENT

    refresh_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/refresh",
        json_data=get_refresh_data(refresh_token),
    )

    async with refresh_response:
        body = await refresh_response.json()

        assert refresh_response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Refresh token has been revoked"


@pytest.mark.asyncio
async def test_logout_with_invalid_token(make_post_request) -> None:
    """Проверяет logout с неизвестным refresh-токеном."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/logout",
        json_data=get_invalid_refresh_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_logout_others(
    registered_user,
    registered_user_tokens,
    logged_in_user_tokens,
    make_post_request,
    get_refresh_sessions_by_user_id,
) -> None:
    """Проверяет отзыв всех refresh-сессий, кроме текущей."""
    old_token = registered_user_tokens["refresh_token"]
    current_token = logged_in_user_tokens["refresh_token"]

    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/logout-others",
        json_data=get_logout_data(current_token),
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    sessions = await get_refresh_sessions_by_user_id(registered_user["id"])

    assert len(sessions) == 2
    assert sum(item["revoked_at"] is not None for item in sessions) == 1
    assert sum(item["revoked_at"] is None for item in sessions) == 1

    old_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/refresh",
        json_data=get_refresh_data(old_token),
    )

    async with old_response:
        old_body = await old_response.json()

        assert old_response.status == HTTPStatus.UNAUTHORIZED
        assert old_body["detail"] == "Refresh token has been revoked"

    current_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/refresh",
        json_data=get_refresh_data(current_token),
    )

    async with current_response:
        current_body = await current_response.json()

        assert current_response.status == HTTPStatus.OK
        assert_token_pair_response(current_body)


@pytest.mark.asyncio
async def test_logout_others_with_invalid_token(make_post_request) -> None:
    """Проверяет logout-others с неизвестным токеном."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/logout-others",
        json_data=get_invalid_refresh_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Invalid refresh token"


@pytest.mark.parametrize(
    "endpoint",
    ["logout", "logout-others"],
)
@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"refresh_token": None},
        {"refresh_token": 123},
        {"token": "wrong-field"},
    ],
)
@pytest.mark.asyncio
async def test_logout_with_invalid_payload(
    make_post_request,
    endpoint,
    payload,
) -> None:
    """Проверяет валидацию logout и logout-others."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/{endpoint}",
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]
