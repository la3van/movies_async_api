"""Асинхронный HTTP-клиент Auth Service."""

import httpx
from auth.exceptions import (
    AuthServiceContractError,
    AuthServiceUnavailableError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from auth.models import AuthServiceUser
from core.config import get_settings
from pydantic import ValidationError


class AuthServiceClient:
    """Проверить токен через существующий GET /users/me."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def get_current_user(
        self,
        *,
        token: str,
        forwarded_headers: dict[str, str],
    ) -> AuthServiceUser:
        headers = {**forwarded_headers, "Authorization": f"Bearer {token}"}
        try:
            response = await self._client.get("users/me", headers=headers)
        except httpx.RequestError as error:
            raise AuthServiceUnavailableError(
                "Auth Service is unavailable"
            ) from error

        if response.status_code in {401, 404}:
            raise InvalidAccessTokenError("Auth Service rejected access token")
        if response.status_code == 403:
            raise AuthUserForbiddenError("Auth Service rejected user")
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise AuthServiceUnavailableError(
                "Auth Service is temporarily unavailable"
            )
        if response.status_code != 200:
            raise AuthServiceContractError(
                f"Unexpected Auth Service status: {response.status_code}"
            )

        try:
            user = AuthServiceUser.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise AuthServiceContractError(
                "Invalid Auth Service response"
            ) from error
        if not user.is_active:
            raise AuthUserForbiddenError("User is inactive")
        return user

    async def close(self) -> None:
        await self._client.aclose()


auth_client: AuthServiceClient | None = None


async def init_auth_client() -> None:
    """Создать общий HTTP-клиент Auth Service."""
    global auth_client
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=settings.auth_service_connect_timeout,
        read=settings.auth_service_read_timeout,
        write=settings.auth_service_read_timeout,
        pool=settings.auth_service_connect_timeout,
    )
    auth_client = AuthServiceClient(
        httpx.AsyncClient(
            base_url=settings.auth_service_base_url,
            timeout=timeout,
            follow_redirects=False,
        )
    )


async def close_auth_client() -> None:
    """Закрыть общий HTTP-клиент."""
    global auth_client
    if auth_client is not None:
        await auth_client.close()
    auth_client = None


async def get_auth_client() -> AuthServiceClient:
    """Вернуть инициализированный клиент."""
    if auth_client is None:
        raise RuntimeError("Auth Service client is not initialized")
    return auth_client
