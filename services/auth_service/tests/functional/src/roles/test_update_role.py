"""Функциональные тесты обновления ролей."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.roles import (
    MISSING_ROLE_ID,
    UPDATED_ROLE_DESCRIPTION,
    UPDATED_ROLE_NAME,
    get_full_role_update_data,
    get_role_update_data,
    get_second_role_create_data,
)


@pytest.mark.asyncio
async def test_update_role(
    created_role,
    created_second_permission,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление всех полей роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_full_role_update_data(
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
        assert [permission['id'] for permission in body['permissions']] == [
            created_second_permission['id'],
        ]


@pytest.mark.asyncio
async def test_update_role_partial_fields(
    created_role,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет частичный PATCH роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(description='Only description'),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['name'] == created_role['name']
        assert body['description'] == 'Only description'
        assert body['is_default'] == created_role['is_default']


@pytest.mark.asyncio
async def test_update_role_clears_nullable_and_list_fields(
    created_role,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет очистку description и permission_ids."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(
            description=None,
            permission_ids=[],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['description'] is None
        assert body['permissions'] == []


@pytest.mark.asyncio
async def test_update_role_with_empty_payload(
    created_role,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет допустимый пустой PATCH роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == created_role


@pytest.mark.asyncio
async def test_update_role_with_same_name(
    created_role,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет PATCH с текущим именем без ложного конфликта."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(name=created_role['name']),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['name'] == created_role['name']


@pytest.mark.asyncio
async def test_update_role_to_duplicate_name(
    created_role,
    superuser_headers,
    make_post_request,
    make_patch_request,
) -> None:
    """Проверяет конфликт при обновлении имени роли."""
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
        json_data=get_role_update_data(name=created_role['name']),
        headers=superuser_headers,
    )

    async with update_response:
        body = await update_response.json()

        assert update_response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Role already exists'


@pytest.mark.asyncio
async def test_update_role_with_missing_permission(
    created_role,
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление роли отсутствующим permission."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(
            permission_ids=[
                '00000000-0000-0000-0000-000000000001',
            ],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Some permissions were not found'


@pytest.mark.asyncio
async def test_update_missing_role(
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет обновление отсутствующей роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{MISSING_ROLE_ID}',
        json_data=get_role_update_data(name='new-name'),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_update_role_invalidates_related_caches(
    user_with_role,
    created_role,
    created_second_permission,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_patch_request,
) -> None:
    """Проверяет инвалидацию role item/list и user profile."""
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
        assert list_response.status == HTTPStatus.OK

    user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )
    async with user_response:
        cached_user = await user_response.json()

        assert user_response.status == HTTPStatus.OK
        assert cached_user['roles'][0]['name'] == created_role['name']

    update_response = await make_patch_request(
        url=item_url,
        json_data=get_full_role_update_data(
            permission_ids=[created_second_permission['id']],
        ),
        headers=superuser_headers,
    )
    async with update_response:
        updated_role = await update_response.json()

        assert update_response.status == HTTPStatus.OK

    fresh_item_response = await make_get_request(
        url=item_url,
        headers=superuser_headers,
    )
    async with fresh_item_response:
        fresh_role = await fresh_item_response.json()

        assert fresh_item_response.status == HTTPStatus.OK
        assert fresh_role == updated_role

    fresh_list_response = await make_get_request(
        url=list_url,
        headers=superuser_headers,
        query_data={'limit': 10, 'offset': 0},
    )
    async with fresh_list_response:
        fresh_list = await fresh_list_response.json()

        assert fresh_list_response.status == HTTPStatus.OK
        assert fresh_list[0] == updated_role

    fresh_user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )
    async with fresh_user_response:
        fresh_user = await fresh_user_response.json()

        assert fresh_user_response.status == HTTPStatus.OK
        assert fresh_user['roles'][0]['name'] == UPDATED_ROLE_NAME
        assert fresh_user['roles'][0]['permissions'][0]['id'] == (
            created_second_permission['id']
        )
        assert fresh_user != cached_user


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {'name': ''},
        {'name': 'x' * 101},
        {'name': 123},
        {'description': 123},
        {'is_default': 'invalid'},
        {'permission_ids': 'invalid'},
        {'permission_ids': ['invalid-uuid']},
    ],
)
@pytest.mark.asyncio
async def test_update_role_with_invalid_payload(
    created_role,
    superuser_headers,
    make_patch_request,
    payload,
) -> None:
    """Проверяет валидацию тела PATCH роли."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=payload,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_update_role_with_invalid_uuid(
    superuser_headers,
    make_patch_request,
) -> None:
    """Проверяет валидацию UUID роли в PATCH."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/invalid-uuid',
        json_data=get_role_update_data(name='new-name'),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
async def test_update_role_without_token(
    created_role,
    make_patch_request,
) -> None:
    """Проверяет запрет обновления роли без токена."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(name='new-name'),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_update_role_by_regular_user(
    created_role,
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет запрет обновления роли обычным пользователем."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/roles/{created_role["id"]}',
        json_data=get_role_update_data(name='new-name'),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'
