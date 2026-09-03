"""Функциональные тесты обновления permissions."""

from http import HTTPStatus
from typing import Any

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.permissions import (
    MISSING_PERMISSION_ID,
    UPDATED_PERMISSION_CODE,
    UPDATED_PERMISSION_DESCRIPTION,
    get_full_permission_update_data,
    get_permission_update_data,
)

PERMISSIONS_URL = f"{test_settings.api_prefix}/permissions/"


def _assert_validation_error(
    body: dict[str, Any],
    field: str,
) -> None:
    """Проверяет наличие ошибки валидации указанного поля."""
    assert isinstance(body.get("detail"), list)
    assert any(
        error.get("loc", [])[-1:] == [field] for error in body["detail"]
    )


def _get_permission_url(permission_id: str) -> str:
    """Возвращает URL одной permission."""
    return f"{test_settings.api_prefix}/permissions/{permission_id}"


@pytest.mark.asyncio
async def test_update_permission(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление всех полей permission."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_full_permission_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body["id"] == created_permission["id"]
        assert body["code"] == UPDATED_PERMISSION_CODE
        assert body["description"] == UPDATED_PERMISSION_DESCRIPTION


@pytest.mark.asyncio
async def test_update_permission_code_only(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет частичное обновление только code."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_permission_update_data(
            code=UPDATED_PERMISSION_CODE,
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body["code"] == UPDATED_PERMISSION_CODE
        assert body["description"] == created_permission["description"]


@pytest.mark.asyncio
async def test_update_permission_description_only(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет частичное обновление только description."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_permission_update_data(
            description=UPDATED_PERMISSION_DESCRIPTION,
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body["code"] == created_permission["code"]
        assert body["description"] == UPDATED_PERMISSION_DESCRIPTION


@pytest.mark.asyncio
async def test_update_permission_clear_description(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет явную очистку description через null."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_permission_update_data(description=None),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body["code"] == created_permission["code"]
        assert body["description"] is None


@pytest.mark.asyncio
async def test_update_permission_with_empty_payload(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет пустой PATCH без изменения permission."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_permission_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == created_permission


@pytest.mark.asyncio
async def test_update_permission_with_same_code(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление с прежним code без ложного конфликта."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_permission_update_data(
            code=created_permission["code"],
            description=UPDATED_PERMISSION_DESCRIPTION,
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body["code"] == created_permission["code"]
        assert body["description"] == UPDATED_PERMISSION_DESCRIPTION


@pytest.mark.asyncio
async def test_update_permission_to_duplicate_code(
    created_permission,
    created_second_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет ошибку обновления на существующий code."""
    response = await make_patch_request(
        url=_get_permission_url(created_second_permission["id"]),
        json_data=get_permission_update_data(
            code=created_permission["code"],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body["detail"] == "Permission already exists"


@pytest.mark.asyncio
async def test_update_missing_permission(
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление отсутствующей permission."""
    response = await make_patch_request(
        url=_get_permission_url(MISSING_PERMISSION_ID),
        json_data=get_full_permission_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body["detail"] == "Permission not found"


@pytest.mark.asyncio
async def test_update_permission_with_invalid_uuid(
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет валидацию UUID при обновлении permission."""
    response = await make_patch_request(
        url=_get_permission_url("invalid-uuid"),
        json_data=get_full_permission_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        _assert_validation_error(body, "permission_id")


@pytest.mark.asyncio
async def test_update_permission_without_body(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет ошибку обновления без request body."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "error_field"),
    [
        ({"code": ""}, "code"),
        ({"code": "x" * 101}, "code"),
        ({"code": 123}, "code"),
        ({"description": 123}, "description"),
    ],
)
async def test_update_permission_with_invalid_payload(
    created_permission,
    superuser_headers,
    make_patch_request,
    payload: dict[str, Any],
    error_field: str,
) -> None:
    """Проверяет валидацию тела PATCH permission."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=payload,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        _assert_validation_error(body, error_field)


@pytest.mark.asyncio
async def test_update_permission_by_regular_user(
    created_permission,
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет запрет обновления обычным пользователем."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_full_permission_update_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body["detail"] == "Not enough permissions"


@pytest.mark.asyncio
async def test_update_permission_without_token(
    created_permission,
    make_patch_request,
) -> None:
    """Проверяет запрет обновления без access-токена."""
    response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_full_permission_update_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_update_permission_invalidates_item_and_list_cache(
    created_permission,
    superuser_headers,
    make_get_request,
    make_patch_request,
) -> None:
    """Проверяет инвалидацию кешей permission и списка после PATCH."""
    permission_url = _get_permission_url(created_permission["id"])
    query_data = {
        "limit": 10,
        "offset": 0,
    }

    item_response = await make_get_request(
        url=permission_url,
        headers=superuser_headers,
    )
    async with item_response:
        item_body = await item_response.json()
        assert item_response.status == HTTPStatus.OK
        assert item_body == created_permission

    list_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data=query_data,
    )
    async with list_response:
        list_body = await list_response.json()
        assert list_response.status == HTTPStatus.OK
        assert list_body == [created_permission]

    update_response = await make_patch_request(
        url=permission_url,
        json_data=get_full_permission_update_data(),
        headers=superuser_headers,
    )
    async with update_response:
        updated_permission = await update_response.json()
        assert update_response.status == HTTPStatus.OK

    refreshed_item_response = await make_get_request(
        url=permission_url,
        headers=superuser_headers,
    )
    async with refreshed_item_response:
        refreshed_item = await refreshed_item_response.json()
        assert refreshed_item_response.status == HTTPStatus.OK
        assert refreshed_item == updated_permission

    refreshed_list_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data=query_data,
    )
    async with refreshed_list_response:
        refreshed_list = await refreshed_list_response.json()
        assert refreshed_list_response.status == HTTPStatus.OK
        assert refreshed_list == [updated_permission]


@pytest.mark.asyncio
async def test_update_permission_invalidates_role_and_user_cache(
    created_permission,
    created_role,
    user_with_role,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_patch_request,
) -> None:
    """Проверяет каскадную инвалидацию role и user cache."""
    role_url = f"{test_settings.api_prefix}/roles/{created_role['id']}"
    roles_url = f"{test_settings.api_prefix}/roles/"
    user_url = f"{test_settings.api_prefix}/users/me"

    cached_role_response = await make_get_request(
        url=role_url,
        headers=superuser_headers,
    )
    async with cached_role_response:
        cached_role = await cached_role_response.json()
        assert cached_role_response.status == HTTPStatus.OK
        assert (
            cached_role["permissions"][0]["code"] == created_permission["code"]
        )

    cached_roles_response = await make_get_request(
        url=roles_url,
        headers=superuser_headers,
        query_data={
            "limit": 10,
            "offset": 0,
        },
    )
    async with cached_roles_response:
        cached_roles = await cached_roles_response.json()
        assert cached_roles_response.status == HTTPStatus.OK
        assert (
            cached_roles[0]["permissions"][0]["code"]
            == (created_permission["code"])
        )

    cached_user_response = await make_get_request(
        url=user_url,
        headers=auth_headers,
    )
    async with cached_user_response:
        cached_user = await cached_user_response.json()
        assert cached_user_response.status == HTTPStatus.OK
        assert cached_user["id"] == user_with_role["id"]
        assert (
            cached_user["roles"][0]["permissions"][0]["code"]
            == (created_permission["code"])
        )

    update_response = await make_patch_request(
        url=_get_permission_url(created_permission["id"]),
        json_data=get_full_permission_update_data(),
        headers=superuser_headers,
    )
    async with update_response:
        updated_permission = await update_response.json()
        assert update_response.status == HTTPStatus.OK

    refreshed_role_response = await make_get_request(
        url=role_url,
        headers=superuser_headers,
    )
    async with refreshed_role_response:
        refreshed_role = await refreshed_role_response.json()
        assert refreshed_role_response.status == HTTPStatus.OK
        assert refreshed_role["permissions"][0] == updated_permission

    refreshed_roles_response = await make_get_request(
        url=roles_url,
        headers=superuser_headers,
        query_data={
            "limit": 10,
            "offset": 0,
        },
    )
    async with refreshed_roles_response:
        refreshed_roles = await refreshed_roles_response.json()
        assert refreshed_roles_response.status == HTTPStatus.OK
        assert refreshed_roles[0]["permissions"][0] == updated_permission

    refreshed_user_response = await make_get_request(
        url=user_url,
        headers=auth_headers,
    )
    async with refreshed_user_response:
        refreshed_user = await refreshed_user_response.json()
        assert refreshed_user_response.status == HTTPStatus.OK
        assert refreshed_user["roles"][0]["permissions"][0] == (
            updated_permission
        )
