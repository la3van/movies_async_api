"""Функциональные тесты регистрации пользователя."""

from http import HTTPStatus

import pytest

from tests.functional.settings import test_settings
from tests.functional.test_data.auth import (
    SECOND_USER_LOGIN,
    VALID_USER_EMAIL,
    VALID_USER_LOGIN,
    get_duplicate_email_register_data,
    get_duplicate_login_register_data,
    get_register_data,
    get_second_register_data,
)
from tests.functional.test_data.roles import get_role_create_data
from tests.functional.utils.helpers import (
    assert_token_pair_response,
    build_auth_headers,
)


@pytest.mark.asyncio
async def test_register_user(
    make_post_request,
    get_user_by_login,
    get_login_history_by_login,
) -> None:
    """Проверяет регистрацию, создание сессии и истории входа."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=get_register_data(),
        headers={"User-Agent": "auth-tests/register"},
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert_token_pair_response(body)

    user = await get_user_by_login(VALID_USER_LOGIN)

    assert user is not None
    assert user["login"] == VALID_USER_LOGIN
    assert user["email"] == VALID_USER_EMAIL
    assert user["is_active"] is True
    assert user["is_superuser"] is False

    login_history = await get_login_history_by_login(VALID_USER_LOGIN)

    assert len(login_history) == 1
    assert login_history[0]["is_successful"] is True
    assert login_history[0]["reason"] is None
    assert login_history[0]["user_agent"] == "auth-tests/register"
    assert login_history[0]["ip_address"] is not None


@pytest.mark.asyncio
async def test_register_user_without_optional_names(
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет регистрацию без необязательных имени и фамилии."""
    payload = get_register_data()
    payload.pop("first_name")
    payload.pop("last_name")

    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CREATED
        assert_token_pair_response(body)

    profile_response = await make_get_request(
        url=f"{test_settings.api_prefix}/users/me",
        headers=build_auth_headers(body["access_token"]),
    )

    async with profile_response:
        profile = await profile_response.json()

        assert profile_response.status == HTTPStatus.OK
        assert profile["first_name"] is None
        assert profile["last_name"] is None


@pytest.mark.asyncio
async def test_register_user_receives_default_role(
    superuser_headers,
    make_post_request,
    make_get_request,
) -> None:
    """Проверяет назначение новой учётной записи роли по умолчанию."""
    role_response = await make_post_request(
        url=f"{test_settings.api_prefix}/roles/",
        json_data=get_role_create_data(is_default=True),
        headers=superuser_headers,
    )

    async with role_response:
        role = await role_response.json()

        assert role_response.status == HTTPStatus.CREATED
        assert role["is_default"] is True

    register_response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=get_second_register_data(),
    )

    async with register_response:
        assert register_response.status == HTTPStatus.CREATED, (
            await register_response.text()
        )

        tokens = await register_response.json()

    profile_response = await make_get_request(
        url=f"{test_settings.api_prefix}/users/me",
        headers=build_auth_headers(tokens["access_token"]),
    )

    async with profile_response:
        profile = await profile_response.json()

        assert profile_response.status == HTTPStatus.OK
        assert profile["login"] == SECOND_USER_LOGIN
        assert [item["id"] for item in profile["roles"]] == [role["id"]]


@pytest.mark.asyncio
async def test_register_user_with_existing_login(
    registered_user,
    make_post_request,
) -> None:
    """Проверяет ошибку регистрации с существующим login."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=get_duplicate_login_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body["detail"] == "User with this login already exists"


@pytest.mark.asyncio
async def test_register_user_with_existing_email(
    registered_user,
    make_post_request,
) -> None:
    """Проверяет ошибку регистрации с существующим email."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=get_duplicate_email_register_data(),
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.CONFLICT
        assert body["detail"] == "User with this email already exists"


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {
            "email": VALID_USER_EMAIL,
            "password": "password123",
        },
        {
            "login": VALID_USER_LOGIN,
            "password": "password123",
        },
        {
            "login": VALID_USER_LOGIN,
            "email": VALID_USER_EMAIL,
        },
        get_register_data(login=""),
        get_register_data(login="x" * 101),
        get_register_data(login=None),
        get_register_data(login=123),
        get_register_data(email="not-an-email"),
        get_register_data(email=None),
        get_register_data(password="short"),
        get_register_data(password="x" * 129),
        get_register_data(password=None),
        get_register_data(first_name="x" * 256),
        get_register_data(last_name="x" * 256),
    ],
)
@pytest.mark.asyncio
async def test_register_user_with_invalid_payload(
    make_post_request,
    payload,
) -> None:
    """Проверяет валидацию тела запроса регистрации."""
    response = await make_post_request(
        url=f"{test_settings.api_prefix}/auth/register",
        json_data=payload,
    )

    async with response:
        body = await response.json()

        assert response.status == HTTPStatus.UNPROCESSABLE_ENTITY
        assert body["detail"]
