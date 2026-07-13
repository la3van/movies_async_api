"""Функциональные тесты назначения ролей пользователям."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.roles import MISSING_ROLE_ID

MISSING_USER_ID = '00000000-0000-0000-0000-000000000003'


def build_user_role_url(user_id: str, role_id: str) -> str:
    """Формирует URL управления ролью пользователя."""
    return (
        f'{test_settings.api_prefix}/users/{user_id}/roles/{role_id}'
    )


@pytest.mark.asyncio
async def test_assign_role_to_user(
    registered_user,
    created_role,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет назначение роли пользователю."""
    response = await make_post_request(
        url=build_user_role_url(
            registered_user['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == registered_user['id']
        assert [role['id'] for role in body['roles']] == [
            created_role['id'],
        ]


@pytest.mark.asyncio
async def test_assign_same_role_is_idempotent(
    user_with_role,
    created_role,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет повторное назначение уже назначенной роли."""
    response = await make_post_request(
        url=build_user_role_url(
            user_with_role['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert len(body['roles']) == 1
        assert body['roles'][0]['id'] == created_role['id']


@pytest.mark.asyncio
async def test_assign_role_invalidates_user_cache(
    registered_user,
    created_role,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_post_request,
) -> None:
    """Проверяет очистку кеша профиля после назначения роли."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body['roles'] == []

    assign_response = await make_post_request(
        url=build_user_role_url(
            registered_user['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with assign_response:
        assert assign_response.status == HTTPStatus.OK

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert [role['id'] for role in second_body['roles']] == [
            created_role['id'],
        ]


@pytest.mark.asyncio
async def test_remove_role_from_user(
    user_with_role,
    created_role,
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет удаление роли у пользователя."""
    response = await make_delete_request(
        url=build_user_role_url(
            user_with_role['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == user_with_role['id']
        assert body['roles'] == []


@pytest.mark.asyncio
async def test_remove_unassigned_role_is_idempotent(
    registered_user,
    created_role,
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет удаление роли, которой у пользователя нет."""
    response = await make_delete_request(
        url=build_user_role_url(
            registered_user['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['roles'] == []


@pytest.mark.asyncio
async def test_remove_role_invalidates_user_cache(
    user_with_role,
    created_role,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_delete_request,
) -> None:
    """Проверяет очистку кеша профиля после удаления роли."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body['roles']) == 1

    delete_response = await make_delete_request(
        url=build_user_role_url(
            user_with_role['id'],
            created_role['id'],
        ),
        headers=superuser_headers,
    )

    async with delete_response:
        assert delete_response.status == HTTPStatus.OK

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body['roles'] == []


@pytest.mark.parametrize('method_name', ['post', 'delete'])
@pytest.mark.asyncio
async def test_manage_user_role_without_token(
    registered_user,
    created_role,
    make_post_request,
    make_delete_request,
    method_name,
) -> None:
    """Проверяет запрет управления ролями без access-токена."""
    request = (
        make_post_request
        if method_name == 'post'
        else make_delete_request
    )

    response = await request(
        url=build_user_role_url(
            registered_user['id'],
            created_role['id'],
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.parametrize('method_name', ['post', 'delete'])
@pytest.mark.asyncio
async def test_manage_user_role_by_regular_user(
    registered_user,
    created_role,
    auth_headers,
    make_post_request,
    make_delete_request,
    method_name,
) -> None:
    """Проверяет недостаточные права обычного пользователя."""
    request = (
        make_post_request
        if method_name == 'post'
        else make_delete_request
    )

    response = await request(
        url=build_user_role_url(
            registered_user['id'],
            created_role['id'],
        ),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.parametrize('method_name', ['post', 'delete'])
@pytest.mark.asyncio
async def test_manage_role_for_missing_user(
    created_role,
    superuser_headers,
    make_post_request,
    make_delete_request,
    method_name,
) -> None:
    """Проверяет управление ролью несуществующего пользователя."""
    request = (
        make_post_request
        if method_name == 'post'
        else make_delete_request
    )

    response = await request(
        url=build_user_role_url(MISSING_USER_ID, created_role['id']),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'User not found'


@pytest.mark.parametrize('method_name', ['post', 'delete'])
@pytest.mark.asyncio
async def test_manage_missing_role_for_user(
    registered_user,
    superuser_headers,
    make_post_request,
    make_delete_request,
    method_name,
) -> None:
    """Проверяет управление несуществующей ролью пользователя."""
    request = (
        make_post_request
        if method_name == 'post'
        else make_delete_request
    )

    response = await request(
        url=build_user_role_url(
            registered_user['id'],
            MISSING_ROLE_ID,
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.parametrize('method_name', ['post', 'delete'])
@pytest.mark.parametrize(
    ('user_id', 'role_id'),
    [
        ('invalid-user-id', MISSING_ROLE_ID),
        (MISSING_USER_ID, 'invalid-role-id'),
    ],
)
@pytest.mark.asyncio
async def test_manage_user_role_with_invalid_uuid(
    superuser_headers,
    make_post_request,
    make_delete_request,
    method_name,
    user_id,
    role_id,
) -> None:
    """Проверяет валидацию UUID пользователя и роли."""
    request = (
        make_post_request
        if method_name == 'post'
        else make_delete_request
    )

    response = await request(
        url=build_user_role_url(user_id, role_id),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']
