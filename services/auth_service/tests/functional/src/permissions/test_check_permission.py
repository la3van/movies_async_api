"""Функциональные тесты проверки permissions пользователя."""

from http import HTTPStatus
from typing import Any

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.permissions import PERMISSION_CODE

CHECK_PERMISSION_URL = f"{test_settings.api_prefix}/permissions/check"


def _assert_validation_error(
    body: dict[str, Any],
    field: str,
) -> None:
    """Проверяет наличие ошибки валидации указанного поля."""
    assert isinstance(body.get("detail"), list)
    assert any(
        error.get("loc", [])[-1:] == [field] for error in body["detail"]
    )


@pytest.mark.asyncio
async def test_check_permission_without_permission(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет отсутствие permission у обычного пользователя."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        json_data={
            "permission_code": PERMISSION_CODE,
        },
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == {"has_permission": False}


@pytest.mark.asyncio
async def test_check_permission_with_role_permission(
    user_with_role,
    created_permission,
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет наличие permission через роль пользователя."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        json_data={
            "permission_code": created_permission["code"],
        },
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert user_with_role["roles"]
        assert response.status == HTTPStatus.OK
        assert body == {"has_permission": True}


@pytest.mark.asyncio
async def test_check_permission_for_superuser(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет, что superuser имеет любое permission."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        json_data={
            "permission_code": "unknown:permission",
        },
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == {"has_permission": True}


@pytest.mark.asyncio
async def test_check_permission_without_token(
    make_post_request,
) -> None:
    """Проверяет запрет проверки permission без access-токена."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        json_data={
            "permission_code": PERMISSION_CODE,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_check_permission_without_body(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку проверки permission без request body."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"permission_code": None},
        {"permission_code": ""},
        {"permission_code": "x" * 101},
        {"permission_code": 123},
    ],
)
async def test_check_permission_with_invalid_payload(
    auth_headers,
    make_post_request,
    payload: dict[str, Any],
) -> None:
    """Проверяет валидацию тела запроса проверки permission."""
    response = await make_post_request(
        url=CHECK_PERMISSION_URL,
        json_data=payload,
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        _assert_validation_error(body, "permission_code")
