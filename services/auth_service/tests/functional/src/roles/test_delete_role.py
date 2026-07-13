"""Функциональные тесты удаления ролей."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.roles import MISSING_ROLE_ID


@pytest.mark.asyncio
async def test_delete_role(
    created_role,
    superuser_headers,
    make_delete_request,
    make_get_request,
) -> None:
    """Проверяет удаление роли."""
    delete_response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with delete_response:
        assert delete_response.status == HTTPStatus.NO_CONTENT

    get_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with get_response:
        body = await get_response.json()

        assert get_response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_delete_role_invalidates_related_caches(
    user_with_role,
    created_role,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_delete_request,
) -> None:
    """Проверяет инвалидацию роли, списка и профиля пользователя."""
    item_url = f'{test_settings.api_prefix}/roles/{created_role["id"]}'
    list_url = f'{test_settings.api_prefix}/roles/'

    item_response = await make_get_request(
        url=item_url,
        headers=superuser_headers,
    )
    async with item_response:
        assert item_response.status == HTTPStatus.OK

    list_response = await make_get_request(
        url=list_url,
        headers=superuser_headers,
        query_data={'limit': 10, 'offset': 0},
    )
    async with list_response:
        role_list = await list_response.json()

        assert list_response.status == HTTPStatus.OK
        assert len(role_list) == 1

    user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )
    async with user_response:
        user = await user_response.json()

        assert user_response.status == HTTPStatus.OK
        assert len(user['roles']) == 1

    delete_response = await make_delete_request(
        url=item_url,
        headers=superuser_headers,
    )
    async with delete_response:
        assert delete_response.status == HTTPStatus.NO_CONTENT

    fresh_item_response = await make_get_request(
        url=item_url,
        headers=superuser_headers,
    )
    async with fresh_item_response:
        body = await fresh_item_response.json()

        assert fresh_item_response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'

    fresh_list_response = await make_get_request(
        url=list_url,
        headers=superuser_headers,
        query_data={'limit': 10, 'offset': 0},
    )
    async with fresh_list_response:
        fresh_list = await fresh_list_response.json()

        assert fresh_list_response.status == HTTPStatus.OK
        assert fresh_list == []

    fresh_user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )
    async with fresh_user_response:
        fresh_user = await fresh_user_response.json()

        assert fresh_user_response.status == HTTPStatus.OK
        assert fresh_user['roles'] == []


@pytest.mark.asyncio
async def test_delete_missing_role(
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет удаление отсутствующей роли."""
    response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_delete_role_with_invalid_uuid(
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет валидацию UUID роли при удалении."""
    response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/invalid-uuid',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_delete_role_without_token(
    created_role,
    make_delete_request,
) -> None:
    """Проверяет запрет удаления роли без токена."""
    response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_delete_role_by_regular_user(
    created_role,
    auth_headers,
    make_delete_request,
) -> None:
    """Проверяет запрет удаления роли обычным пользователем."""
    response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'
