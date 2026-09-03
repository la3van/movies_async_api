"""HTTP-клиент для Auth Service."""

import httpx
from auth.exceptions import (
    AuthServiceContractError,
    AuthServiceUnavailableError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from core.config import get_settings
from pydantic import BaseModel, StrictBool, ValidationError


class PermissionCheckResponse(BaseModel):
    """Ответ Auth Service на проверку permission."""

    has_permission: StrictBool


class AuthServiceClient:
    """Выполняет запросы к Auth Serivce."""

    def __init__(
        self,
        client: httpx.AsyncClient,
    ) -> None:
        self._client = client

    async def check_permission(
        self,
        token: str,
        permission_code: str,
        forwarded_headers: dict[str, str],
    ) -> bool:
        """Проверяет permission через Auth Service."""
        headers = {
            **forwarded_headers,
            "Authorization": f"Bearer {token}",
        }

        try:
            response = await self._client.post(
                "permissions/check",
                json={
                    "permission_code": permission_code,
                },
                headers=headers,
            )
        except httpx.RequestError as error:
            raise AuthServiceUnavailableError(
                "Auth Service is unavailable",
            ) from error

        if response.status_code in {
            401,
            404,
        }:
            raise InvalidAccessTokenError(
                "Auth Service rejected access token",
            )

        if response.status_code == 403:
            raise AuthUserForbiddenError(
                "Auth Service rejected user",
            )

        if (
            response.status_code == 408
            or response.status_code == 429
            or response.status_code >= 500
        ):
            raise AuthServiceUnavailableError(
                "Auth Service is temporarily unavailable",
            )

        if response.status_code != 200:
            raise AuthServiceContractError(
                (f"Unexpected Auth Service status: {response.status_code}"),
            )

        try:
            response_data = PermissionCheckResponse.model_validate(
                response.json(),
            )
        except (ValueError, ValidationError) as error:
            raise AuthServiceContractError(
                "Invalid Auth Service response",
            ) from error

        return response_data.has_permission

    async def close(self) -> None:
        """Закрывает HTTP-клиент."""
        await self._client.aclose()


auth_client: AuthServiceClient | None = None


async def init_auth_client() -> None:
    """Создаёт общий HTTP-клиент Auth Service."""
    global auth_client

    settings = get_settings()

    timeout = httpx.Timeout(
        connect=settings.auth_service_connect_timeout,
        read=settings.auth_service_read_timeout,
        write=settings.auth_service_read_timeout,
        pool=settings.auth_service_connect_timeout,
    )

    http_client = httpx.AsyncClient(
        base_url=settings.auth_service_base_url,
        timeout=timeout,
    )

    auth_client = AuthServiceClient(http_client)


async def close_auth_client() -> None:
    """Закрывает HTTP-клиент Auth Service."""
    global auth_client

    if auth_client is not None:
        await auth_client.close()
        auth_client = None


async def get_auth_client() -> AuthServiceClient:
    """Возвращает инициализированный Auth Service client."""
    if auth_client is None:
        raise RuntimeError(
            "Auth Service client is not initialized",
        )

    return auth_client
