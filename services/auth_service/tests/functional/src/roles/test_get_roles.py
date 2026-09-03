"""Функциональные тесты получения ролей."""

from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.responses import ROLE_RESPONSE_FIELDS
from tests.functional.test_data.roles import (
    MISSING_ROLE_ID,
    get_second_role_create_data,
)
from tests.functional.utils.helpers import assert_has_fields


@pytest.mark.asyncio
async def test_get_roles(
    created_role,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение списка ролей."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data={"limit": 10, "offset": 0},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert len(body) == 1
        assert body[0]["id"] == created_role["id"]
        assert_has_fields(body[0], ROLE_RESPONSE_FIELDS)


@pytest.mark.asyncio
async def test_get_empty_roles_list(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение пустого списка ролей."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.asyncio
async def test_get_roles_with_pagination(
    created_role,
    superuser_headers,
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет limit и offset списка ролей."""
    create_response = await make_post_request(
        url=f"{test_settings.api_prefix}/roles/",
        json_data=get_second_role_create_data(),
        headers=superuser_headers,
    )

    async with create_response:
        second_role = await create_response.json()

        assert create_response.status == HTTPStatus.CREATED

    full_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data={"limit": 10, "offset": 0},
    )

    async with full_response:
        full_body = await full_response.json()

        assert full_response.status == HTTPStatus.OK
        assert {role["id"] for role in full_body} == {
            created_role["id"],
            second_role["id"],
        }

    page_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data={"limit": 1, "offset": 1},
    )

    async with page_response:
        page_body = await page_response.json()

        assert page_response.status == HTTPStatus.OK
        assert page_body == [full_body[1]]


@pytest.mark.asyncio
async def test_get_roles_from_cache(
    created_role,
    superuser_headers,
    make_get_request,
    delete_role_by_id,
) -> None:
    """Проверяет возврат списка из Redis после удаления роли в БД."""
    first_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data={"limit": 10, "offset": 0},
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert [role["id"] for role in first_body] == [created_role["id"]]

    await delete_role_by_id(created_role["id"])

    second_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data={"limit": 10, "offset": 0},
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_role_by_id(
    created_role,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение роли по UUID."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/{created_role['id']}",
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_has_fields(body, ROLE_RESPONSE_FIELDS)
        assert body == created_role


@pytest.mark.asyncio
async def test_get_role_by_id_from_cache(
    created_role,
    superuser_headers,
    make_get_request,
    delete_role_by_id,
) -> None:
    """Проверяет возврат роли из Redis после удаления строки в БД."""
    first_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/{created_role['id']}",
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK

    await delete_role_by_id(created_role["id"])

    second_response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/{created_role['id']}",
        headers=superuser_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_missing_role(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение отсутствующей роли."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}",
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body["detail"] == "Role not found"


@pytest.mark.parametrize(
    "query_data",
    [
        {"limit": 0},
        {"limit": -1},
        {"limit": 501},
        {"limit": "invalid"},
        {"offset": -1},
        {"offset": "invalid"},
    ],
)
@pytest.mark.asyncio
async def test_get_roles_with_invalid_query(
    superuser_headers,
    make_get_request,
    query_data,
) -> None:
    """Проверяет валидацию пагинации списка ролей."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/",
        headers=superuser_headers,
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]


@pytest.mark.asyncio
async def test_get_role_with_invalid_uuid(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию UUID роли."""
    response = await make_get_request(
        url=f"{test_settings.api_prefix}/roles/invalid-uuid",
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]


@pytest.mark.parametrize(
    "url",
    [
        f"{test_settings.api_prefix}/roles/",
        f"{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}",
    ],
)
@pytest.mark.asyncio
async def test_get_roles_without_token(
    make_get_request,
    url,
) -> None:
    """Проверяет запрет GET-запросов ролей без токена."""
    response = await make_get_request(url=url)

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body["detail"] == "Not authenticated"


@pytest.mark.parametrize(
    "url",
    [
        f"{test_settings.api_prefix}/roles/",
        f"{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}",
    ],
)
@pytest.mark.asyncio
async def test_get_roles_by_regular_user(
    auth_headers,
    make_get_request,
    url,
) -> None:
    """Проверяет недостаточные права обычного пользователя."""
    response = await make_get_request(url=url, headers=auth_headers)

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body["detail"] == "Not enough permissions"
