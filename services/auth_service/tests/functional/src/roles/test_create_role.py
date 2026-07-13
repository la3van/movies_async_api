"""Функциональные тесты создания ролей."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.responses import ROLE_RESPONSE_FIELDS
from tests.functional.test_data.roles import (
    ROLE_NAME,
    get_role_create_data,
    get_role_with_missing_permission_data,
)
from tests.functional.utils.helpers import assert_has_fields


@pytest.mark.asyncio
async def test_create_role(
    created_permission,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание роли с permission."""
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
async def test_create_role_without_permissions(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание роли с пустым списком permissions."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(permission_ids=[]),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert body['permissions'] == []
        assert body['is_default'] is False


@pytest.mark.asyncio
async def test_create_role_invalidates_list_cache(
    superuser_headers,
    make_get_request,
    make_post_request,
) -> None:
    """Проверяет инвалидацию закешированного списка после POST."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/',
        headers=superuser_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == []

    create_response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(),
        headers=superuser_headers,
    )

    async with create_response:
        created_role = await create_response.json()

        assert create_response.status == HTTPStatus.CREATED

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/roles/',
        headers=superuser_headers,
        query_data={'limit': 10, 'offset': 0},
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert [role['id'] for role in second_body] == [
            created_role['id'],
        ]


@pytest.mark.asyncio
async def test_create_duplicate_role(
    created_role,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание роли с существующим name."""
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
    """Проверяет создание роли с отсутствующим permission."""
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
async def test_create_role_without_token(make_post_request) -> None:
    """Проверяет запрет создания роли без токена."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=get_role_create_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


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


@pytest.mark.parametrize(
    'payload',
    [
        None,
        {},
        {'description': 'No name'},
        get_role_create_data(name=''),
        get_role_create_data(name='x' * 101),
        get_role_create_data(name=None),
        get_role_create_data(name=123),
        get_role_create_data(description=123),
        get_role_create_data(is_default='invalid'),
        {
            'name': 'role',
            'description': None,
            'is_default': False,
            'permission_ids': 'invalid',
        },
        get_role_create_data(permission_ids=['invalid-uuid']),
    ],
)
@pytest.mark.asyncio
async def test_create_role_with_invalid_payload(
    superuser_headers,
    make_post_request,
    payload,
) -> None:
    """Проверяет валидацию тела запроса создания роли."""
    response = await make_post_request(
        url=f'{test_settings.api_prefix}/roles/',
        json_data=payload,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']
