"""Функциональные тесты получения permissions."""
from http import HTTPStatus
from typing import Any

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.permissions import MISSING_PERMISSION_ID
from tests.functional.test_data.responses import PERMISSION_RESPONSE_FIELDS
from tests.functional.utils.helpers import assert_has_fields

PERMISSIONS_URL = f'{test_settings.api_prefix}/permissions/'


def _assert_validation_error(
    body: dict[str, Any],
    field: str,
) -> None:
    """Проверяет наличие ошибки валидации указанного поля."""
    assert isinstance(body.get('detail'), list)
    assert any(
        error.get('loc', [])[-1:] == [field]
        for error in body['detail']
    )


@pytest.mark.asyncio
async def test_get_empty_permissions_list(
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет получение пустого списка permissions."""
    response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body == []


@pytest.mark.asyncio
async def test_get_permissions_with_pagination(
    created_permission,
    created_second_permission,
    superuser_headers,
    make_get_request,
) -> None:
    """Проверяет limit и offset при получении permissions."""
    expected_permissions = sorted(
        [created_permission, created_second_permission],
        key=lambda permission: permission['code'],
    )

    first_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data={
            'limit': 1,
            'offset': 0,
        },
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == [expected_permissions[0]]

    second_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data={
            'limit': 1,
            'offset': 1,
        },
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == [expected_permissions[1]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('query_data', 'error_field'),
    [
        ({'limit': 0, 'offset': 0}, 'limit'),
        ({'limit': -1, 'offset': 0}, 'limit'),
        ({'limit': 501, 'offset': 0}, 'limit'),
        ({'limit': 'invalid', 'offset': 0}, 'limit'),
        ({'limit': 10, 'offset': -1}, 'offset'),
        ({'limit': 10, 'offset': 'invalid'}, 'offset'),
    ],
)
async def test_get_permissions_with_invalid_pagination(
    superuser_headers,
    make_get_request,
    query_data: dict[str, Any],
    error_field: str,
) -> None:
    """Проверяет валидацию параметров пагинации permissions."""
    response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data=query_data,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        _assert_validation_error(body, error_field)


@pytest.mark.asyncio
async def test_get_permissions_list_by_regular_user(
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет запрет чтения списка обычным пользователем."""
    response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_get_permissions_list_without_token(
    make_get_request,
) -> None:
    """Проверяет запрет чтения списка без access-токена."""
    response = await make_get_request(url=PERMISSIONS_URL)

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_get_permissions_list_from_cache(
    created_permission,
    superuser_headers,
    make_get_request,
    delete_permission_by_id,
) -> None:
    """Проверяет получение списка permissions из Redis."""
    query_data = {
        'limit': 10,
        'offset': 0,
    }

    first_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data=query_data,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == [created_permission]

    await delete_permission_by_id(created_permission['id'])

    second_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data=query_data,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


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
        assert body == created_permission


@pytest.mark.asyncio
async def test_get_permission_by_id_from_cache(
    created_permission,
    superuser_headers,
    make_get_request,
    delete_permission_by_id,
) -> None:
    """Проверяет получение одной permission из Redis."""
    permission_url = (
        f'{test_settings.api_prefix}'
        f'/permissions/{created_permission["id"]}'
    )

    first_response = await make_get_request(
        url=permission_url,
        headers=superuser_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == created_permission

    await delete_permission_by_id(created_permission['id'])

    second_response = await make_get_request(
        url=permission_url,
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
    """Проверяет получение отсутствующей permission."""
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{MISSING_PERMISSION_ID}'
        ),
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
        _assert_validation_error(body, 'permission_id')


@pytest.mark.asyncio
async def test_get_permission_by_regular_user(
    created_permission,
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет запрет чтения permission обычным пользователем."""
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_get_permission_without_token(
    created_permission,
    make_get_request,
) -> None:
    """Проверяет запрет чтения permission без access-токена."""
    response = await make_get_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/permissions/{created_permission["id"]}'
        ),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'
