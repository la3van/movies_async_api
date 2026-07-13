"""Функциональные тесты permissions endpoints."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.permissions import (
    MISSING_PERMISSION_ID,
    PERMISSION_CODE,
    PERMISSION_DESCRIPTION,
    UPDATED_PERMISSION_CODE,
    UPDATED_PERMISSION_DESCRIPTION,
    get_duplicate_permission_create_data,
    get_permission_create_data,
    get_permission_update_data,
)
from tests.functional.test_data.responses import PERMISSION_RESPONSE_FIELDS
from tests.functional.utils.helpers import assert_has_fields


@pytest.mark.asyncio
async def test_create_permission(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание permission суперпользователем."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/',
        json_data=get_permission_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert_has_fields(body, PERMISSION_RESPONSE_FIELDS)
        assert body['code'] == PERMISSION_CODE
        assert body['description'] == PERMISSION_DESCRIPTION


@pytest.mark.asyncio
async def test_create_permission_by_regular_user(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет запрет создания permission обычным пользователем."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/',
        json_data=get_permission_create_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_create_duplicate_permission(
    created_permission,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку создания permission с существующим code."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/',
        json_data=get_duplicate_permission_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Permission already exists'


@pytest.mark.asyncio
async def test_get_permissions(
    created_permission,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение списка permissions."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/permissions/',
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
        assert body[0]['id'] == created_permission['id']
        assert body[0]['code'] == created_permission['code']


@pytest.mark.asyncio
async def test_get_permissions_with_invalid_limit(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию limit в списке permissions."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/permissions/',
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
async def test_get_permission_by_id(
    created_permission,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение permission по UUID."""
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_has_fields(body, PERMISSION_RESPONSE_FIELDS)
        assert body['id'] == created_permission['id']
        assert body['code'] == created_permission['code']


@pytest.mark.asyncio
async def test_get_permission_from_redis(
    created_permission,
    superuser_headers,
    make_get_request,
    delete_permission_by_id,
    redis_client,
) -> None:
    """Проверяет получение permission из Redis."""
    await redis_client.flushdb()

    first_response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == created_permission

    await delete_permission_by_id(created_permission['id'])

    second_response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_missing_permission(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет ошибку получения несуществующего permission."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/permissions/{MISSING_PERMISSION_ID}',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Permission not found'


@pytest.mark.asyncio
async def test_get_permission_with_invalid_uuid(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию UUID permission."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/permissions/invalid-uuid',
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_update_permission(
    created_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление permission."""
    response = await make_patch_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        json_data=get_permission_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == created_permission['id']
        assert body['code'] == UPDATED_PERMISSION_CODE
        assert body['description'] == UPDATED_PERMISSION_DESCRIPTION


@pytest.mark.asyncio
async def test_update_permission_refreshes_redis_cache(
    created_permission,
    superuser_headers,
    make_get_request,
    make_patch_request,
    delete_permission_by_id,
    redis_client,
) -> None:
    """Проверяет обновление Redis-кеша после update permission."""
    await redis_client.flushdb()

    first_response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body['code'] == created_permission['code']

    update_response = await make_patch_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        json_data=get_permission_update_data(),
        headers=superuser_headers,
    )

    async with update_response:
        updated_body = await update_response.json()

        assert update_response.status == HTTPStatus.OK
        assert updated_body['code'] == UPDATED_PERMISSION_CODE
        assert updated_body['description'] == UPDATED_PERMISSION_DESCRIPTION
        assert updated_body != first_body

    recache_response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with recache_response:
        recache_body = await recache_response.json()

        assert recache_response.status == HTTPStatus.OK
        assert recache_body == updated_body

    await delete_permission_by_id(created_permission['id'])

    cached_response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=superuser_headers,
    )

    async with cached_response:
        cached_body = await cached_response.json()

        assert cached_response.status == HTTPStatus.OK
        assert cached_body == updated_body


@pytest.mark.asyncio
async def test_update_permission_to_duplicate_code(
    created_permission,
    created_second_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет ошибку обновления permission на существующий code."""
    response = await make_patch_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_second_permission["id"]}'
        ),
        json_data={
            'code': created_permission['code'],
        },
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Permission already exists'


@pytest.mark.asyncio
async def test_check_permission_without_permission(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет отсутствие permission у обычного пользователя."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/check',
        json_data={
            'permission_code': PERMISSION_CODE,
        },
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == {'has_permission': False}


@pytest.mark.asyncio
async def test_check_permission_with_role_permission(
    user_with_role,
    created_permission,
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет наличие permission через роль пользователя."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/check',
        json_data={
            'permission_code': created_permission['code'],
        },
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == {'has_permission': True}


@pytest.mark.asyncio
async def test_check_permission_for_superuser(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет, что superuser имеет любое permission."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/check',
        json_data={
            'permission_code': 'any:permission',
        },
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == {'has_permission': True}


@pytest.mark.asyncio
async def test_check_permission_without_token(
    make_post_request,
) -> None:
    """Проверяет запрет проверки permission без токена."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/permissions/check',
        json_data={
            'permission_code': PERMISSION_CODE,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'
