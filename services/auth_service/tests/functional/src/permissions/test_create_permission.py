"""Функциональные тесты создания permissions."""
from http import HTTPStatus
from typing import Any

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.permissions import (
    PERMISSION_CODE,
    PERMISSION_DESCRIPTION,
    get_duplicate_permission_create_data,
    get_permission_create_data,
)
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
async def test_create_permission(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание permission суперпользователем."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
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
async def test_create_permission_without_description(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет создание permission без необязательного description."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data={
            'code': PERMISSION_CODE,
        },
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert body['code'] == PERMISSION_CODE
        assert body['description'] is None


@pytest.mark.asyncio
async def test_create_duplicate_permission(
    created_permission,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку создания permission с существующим code."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data=get_duplicate_permission_create_data(),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body['detail'] == 'Permission already exists'


@pytest.mark.asyncio
async def test_create_permission_by_regular_user(
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет запрет создания permission обычным пользователем."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data=get_permission_create_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_create_permission_without_token(
    make_post_request,
) -> None:
    """Проверяет запрет создания permission без access-токена."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data=get_permission_create_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_create_permission_without_body(
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку создания permission без request body."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body['detail']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('payload', 'error_field'),
    [
        ({}, 'code'),
        ({'description': PERMISSION_DESCRIPTION}, 'code'),
        ({'code': None}, 'code'),
        ({'code': ''}, 'code'),
        ({'code': 'x' * 101}, 'code'),
        ({'code': 123}, 'code'),
        ({'code': PERMISSION_CODE, 'description': 123}, 'description'),
    ],
)
async def test_create_permission_with_invalid_payload(
    superuser_headers,
    make_post_request,
    payload: dict[str, Any],
    error_field: str,
) -> None:
    """Проверяет валидацию тела запроса создания permission."""
    response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data=payload,
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        _assert_validation_error(body, error_field)


@pytest.mark.asyncio
async def test_create_permission_invalidates_cached_empty_list(
    superuser_headers,
    make_get_request,
    make_post_request,
) -> None:
    """Проверяет очистку кеша пустого списка после создания permission."""
    first_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body == []

    create_response = await make_post_request(
        url=PERMISSIONS_URL,
        json_data=get_permission_create_data(),
        headers=superuser_headers,
    )

    async with create_response:
        created_permission = await create_response.json()

        assert create_response.status == HTTPStatus.CREATED

    second_response = await make_get_request(
        url=PERMISSIONS_URL,
        headers=superuser_headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == [created_permission]
