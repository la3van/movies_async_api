"""Функциональные тесты users endpoints."""
from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    VALID_USER_LOGIN,
    VALID_USER_PASSWORD,
    get_login_data,
    get_refresh_data,
)
from tests.functional.test_data.responses import (
    LOGIN_HISTORY_RESPONSE_FIELDS,
    USER_RESPONSE_FIELDS,
)
from tests.functional.test_data.roles import MISSING_ROLE_ID
from tests.functional.test_data.users import (
    NEW_PASSWORD,
    get_change_password_data,
    get_update_profile_data,
    get_wrong_old_password_data,
)
from tests.functional.utils.helpers import (
    assert_has_fields,
    build_auth_headers,
)


@pytest.mark.asyncio
async def test_get_current_user(
    registered_user,
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет получение текущего пользователя."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert_has_fields(body, USER_RESPONSE_FIELDS)
        assert body['id'] == registered_user['id']
        assert body['login'] == registered_user['login']
        assert body['email'] == registered_user['email']


@pytest.mark.asyncio
async def test_get_current_user_from_redis(
    registered_user_tokens,
    make_get_request,
    delete_user_by_id,
) -> None:
    """Проверяет получение текущего пользователя из Redis."""
    headers = build_auth_headers(registered_user_tokens['access_token'])

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK

    await delete_user_by_id(first_body['id'])

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_current_user_without_token(
    make_get_request,
) -> None:
    """Проверяет запрет получения профиля без токена."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(
    make_get_request,
) -> None:
    """Проверяет запрет получения профиля с невалидным токеном."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers={'Authorization': 'Bearer invalid-token'},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Could not validate credentials'


@pytest.mark.asyncio
async def test_update_current_user(
    registered_user,
    auth_headers,
    make_patch_request,
    make_get_request,
    get_user_by_login,
) -> None:
    """Проверяет обновление профиля текущего пользователя."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert first_body['first_name'] == registered_user['first_name']

    update_response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me',
        json_data=get_update_profile_data(),
        headers=auth_headers,
    )

    async with update_response:
        update_body = await update_response.json()

        assert update_response.status == HTTPStatus.OK
        assert_has_fields(update_body, USER_RESPONSE_FIELDS)
        assert update_body['first_name'] == 'Updated'
        assert update_body['last_name'] == 'User'

    user = await get_user_by_login(VALID_USER_LOGIN)

    assert user is not None
    assert user['first_name'] == 'Updated'
    assert user['last_name'] == 'User'

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == update_body
        assert second_body != first_body


@pytest.mark.asyncio
async def test_change_password(
    auth_headers,
    refresh_token,
    make_patch_request,
    make_post_request,
) -> None:
    """Проверяет смену пароля текущего пользователя."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me/password',
        json_data=get_change_password_data(
            old_password=VALID_USER_PASSWORD,
        ),
        headers=auth_headers,
    )

    async with response:
        assert response.status == HTTPStatus.NO_CONTENT

    old_password_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(
            login=VALID_USER_LOGIN,
            password=VALID_USER_PASSWORD,
        ),
    )

    async with old_password_response:
        body = await old_password_response.json()

        assert old_password_response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid login or password'

    new_password_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(
            login=VALID_USER_LOGIN,
            password=NEW_PASSWORD,
        ),
    )

    async with new_password_response:
        body = await new_password_response.json()

        assert new_password_response.status == HTTPStatus.OK
        assert body['access_token']
        assert body['refresh_token']

    refresh_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/refresh',
        json_data=get_refresh_data(refresh_token),
    )

    async with refresh_response:
        body = await refresh_response.json()

        assert refresh_response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Refresh token has been revoked'


@pytest.mark.asyncio
async def test_change_password_with_wrong_old_password(
    auth_headers,
    make_patch_request,
) -> None:
    """Проверяет ошибку смены пароля с неверным старым паролем."""
    response = await make_patch_request(
        url=f'{test_settings.api_prefix}/users/me/password',
        json_data=get_wrong_old_password_data(),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNAUTHORIZED
        assert body['detail'] == 'Invalid old password'


@pytest.mark.asyncio
async def test_get_login_history(
    registered_user,
    auth_headers,
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет получение истории входов текущего пользователя."""
    login_response = await make_post_request(
        url=f'{test_settings.api_prefix}/auth/login',
        json_data=get_login_data(),
    )

    async with login_response:
        assert login_response.status == HTTPStatus.OK

    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert len(body) == 2
        assert_has_fields(body[0], LOGIN_HISTORY_RESPONSE_FIELDS)
        assert all(item['login'] == registered_user['login'] for item in body)


@pytest.mark.asyncio
async def test_get_login_history_from_redis(
    registered_user_tokens,
    make_get_request,
    delete_login_history_by_user_id,
) -> None:
    """Проверяет получение истории входов из Redis."""
    headers = build_auth_headers(registered_user_tokens['access_token'])

    user_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=headers,
    )

    async with user_response:
        user = await user_response.json()

        assert user_response.status == HTTPStatus.OK

    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body) == 1

    await delete_login_history_by_user_id(user['id'])

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=headers,
        query_data={
            'limit': 10,
            'offset': 0,
        },
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body == first_body


@pytest.mark.asyncio
async def test_get_login_history_with_invalid_limit(
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет валидацию limit в истории входов."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me/login-history',
        headers=auth_headers,
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
async def test_assign_role_to_user(
    registered_user,
    created_role,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет назначение роли пользователю суперпользователем."""
    response = await make_post_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{registered_user["id"]}'
            f'/roles/{created_role["id"]}'
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == registered_user['id']
        assert len(body['roles']) == 1
        assert body['roles'][0]['id'] == created_role['id']


@pytest.mark.asyncio
async def test_assign_role_clears_user_redis_cache(
    user_with_role,
    auth_headers,
    make_get_request,
) -> None:
    """Проверяет очистку кеша пользователя после назначения роли."""
    response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == user_with_role['id']
        assert body['roles'] == user_with_role['roles']
        assert len(body['roles']) == 1


@pytest.mark.asyncio
async def test_assign_role_to_user_by_regular_user(
    registered_user,
    created_role,
    auth_headers,
    make_post_request,
) -> None:
    """Проверяет запрет назначения роли обычным пользователем."""
    response = await make_post_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{registered_user["id"]}'
            f'/roles/{created_role["id"]}'
        ),
        headers=auth_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.FORBIDDEN
        assert body['detail'] == 'Not enough permissions'


@pytest.mark.asyncio
async def test_assign_missing_role_to_user(
    registered_user,
    superuser_headers,
    make_post_request,
) -> None:
    """Проверяет ошибку назначения несуществующей роли."""
    response = await make_post_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{registered_user["id"]}'
            f'/roles/{MISSING_ROLE_ID}'
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.NOT_FOUND
        assert body['detail'] == 'Role not found'


@pytest.mark.asyncio
async def test_remove_role_from_user(
    user_with_role,
    created_role,
    superuser_headers,
    make_delete_request,
) -> None:
    """Проверяет удаление роли у пользователя."""
    response = await make_delete_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{user_with_role["id"]}'
            f'/roles/{created_role["id"]}'
        ),
        headers=superuser_headers,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.OK
        assert body['id'] == user_with_role['id']
        assert body['roles'] == []


@pytest.mark.asyncio
async def test_remove_role_clears_user_redis_cache(
    user_with_role,
    created_role,
    auth_headers,
    superuser_headers,
    make_get_request,
    make_delete_request,
) -> None:
    """Проверяет очистку кеша пользователя после удаления роли."""
    first_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with first_response:
        first_body = await first_response.json()

        assert first_response.status == HTTPStatus.OK
        assert len(first_body['roles']) == 1

    delete_response = await make_delete_request(
        url=(
            f'{test_settings.api_prefix}'
            f'/users/{user_with_role["id"]}'
            f'/roles/{created_role["id"]}'
        ),
        headers=superuser_headers,
    )

    async with delete_response:
        delete_body = await delete_response.json()

        assert delete_response.status == HTTPStatus.OK
        assert delete_body['roles'] == []

    second_response = await make_get_request(
        url=f'{test_settings.api_prefix}/users/me',
        headers=auth_headers,
    )

    async with second_response:
        second_body = await second_response.json()

        assert second_response.status == HTTPStatus.OK
        assert second_body['roles'] == []
