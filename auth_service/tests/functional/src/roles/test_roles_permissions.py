"""Функциональные тесты roles endpoints."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.responses import ROLE_RESPONSE_FIELDS
from tests.functional.test_data.roles import (
    MISSING_ROLE_ID,
    ROLE_NAME,
    UPDATED_ROLE_DESCRIPTION,
    UPDATED_ROLE_NAME,
    get_role_create_data,
    get_role_update_data,
    get_role_with_missing_permission_data,
    get_second_role_create_data,
)
from tests.functional.utils.helpers import assert_has_fields


@pytest.mark.asyncio
async def test_create_role(
    created_permission,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание роли суперпользователем."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(
            permission_ids=[created_permission['id']],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert_has_fields(body, ROLE_RESPONSE_FIELDS)
        assert body['name'] == ROLE_NAME
        assert len(body['permissions']) == 1
        assert body['permissions'][0]['id'] == created_permission['id']


@pytest.mark.asyncio
async def test_create_role_by_regular_user(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет запрет создания роли обычным пользователем."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_create_duplicate_role(
    created_role,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку создания роли с существующим name."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Role already exists'


@pytest.mark.asyncio
async def test_create_role_with_missing_permission(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку создания роли с несуществующим permission."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_with_missing_permission_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Some permissions were not found'


@pytest.mark.asyncio
async def test_get_roles(
    created_role,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение списка ролей."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/',
        headers=superuser_headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert len(body) == 1
        assert body[0]['id'] == created_role['id']
        assert body[0]['name'] == created_role['name']


@pytest.mark.asyncio
async def test_get_roles_with_invalid_limit(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию limit в списке ролей."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/',
        headers=superuser_headers,
        query_data={
            'limit': 0,
            'offset': 0,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_get_role_by_id(
    created_role,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение роли по UUID."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_has_fields(body, ROLE_RESPONSE_FIELDS)
        assert body['id'] == created_role['id']
        assert body['name'] == created_role['name']


@pytest.mark.asyncio
async def test_get_role_from_redis(
    created_role,
    superuser_headers,
    make_get_request,
    delete_role_by_id,
    redis_client,
) -> None:
    """Проверяет получение роли из Redis."""
    await redis_client.flushdb()

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == created_role

    await delete_role_by_id(created_role['id'])

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
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
    """Проверяет ошибку получения несуществующей роли."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_get_role_with_invalid_uuid(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию UUID роли."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/invalid-uuid',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_update_role(
    created_role,
    created_second_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(
            is_default=True,
            permission_ids=[created_second_permission['id']],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == created_role['id']
        assert body['name'] == UPDATED_ROLE_NAME
        assert body['description'] == UPDATED_ROLE_DESCRIPTION
        assert body['is_default'] is True
        assert len(body['permissions']) == 1
        assert body['permissions'][0]['id'] == created_second_permission['id']


@pytest.mark.asyncio
async def test_update_role_refreshes_redis_cache(
    created_role,
    created_second_permission,
    superuser_headers,
    make_get_request,
    make_patch_request,
    delete_role_by_id,
    redis_client,
) -> None:
    """Проверяет обновление Redis-кеша после update role."""
    await redis_client.flushdb()

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body['name'] == created_role['name']

    update_response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(
            is_default=True,
            permission_ids=[created_second_permission['id']],
        ),
        headers=superuser_headers,
    )

    async with update_response:
        updated_body = await update_response.json()

        assert update_response.status == HTTPStatus.OK
        assert updated_body['name'] == UPDATED_ROLE_NAME
        assert updated_body['description'] == UPDATED_ROLE_DESCRIPTION
        assert updated_body != first_body

    recache_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with recache_response:
        recache_body = await recache_response.json()

        assert recache_response.status == HTTPStatus.OK
        assert recache_body == updated_body

    await delete_role_by_id(created_role['id'])

    cached_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with cached_response:
        cached_body = await cached_response.json()

        assert cached_response.status == HTTPStatus.OK
        assert cached_body == updated_body


@pytest.mark.asyncio
async def test_update_role_to_duplicate_name(
    created_role,
    superuser_headers,
    make_post_request,
    make_patch_request,
) -> None:
    """Проверяет ошибку обновления роли на существующий name."""
    create_response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_second_role_create_data(),
        headers=superuser_headers,
    )

    async with create_response:
        second_role = await create_response.json()

        assert create_response.status == HTTPStatus.CREATED

    update_response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{second_role["id"]}',
        json_data={
            'name': created_role['name'],
        },
        headers=superuser_headers,
    )

    async with update_response:
        body = await update_response.json()

        assert update_response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Role already exists'


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
async def test_delete_role_clears_redis_cache(
    created_role,
    superuser_headers,
    make_get_request,
    make_delete_request,
    redis_client,
) -> None:
    """Проверяет очистку Redis-кеша после удаления роли."""
    await redis_client.flushdb()

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body['id'] == created_role['id']

    delete_response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with delete_response:
        assert delete_response.status == HTTPStatus.NO_CONTENT

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        headers=superuser_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.NOT_FOUND
        assert second_body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_delete_missing_role(
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет ошибку удаления несуществующей роли."""
    response = await make_delete_request(
        url=f'{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'
