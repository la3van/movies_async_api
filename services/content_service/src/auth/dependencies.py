"""FastAPI dependencies авторизации."""

from collections.abc import Awaitable, Callable
from typing import Annotated

from auth.client import AuthServiceClient, get_auth_client
from auth.exceptions import (
    AuthServiceContractError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from auth.service import AuthorizationService
from cache.redis import RedisCache
from core.config import Settings, get_settings
from db.redis import get_redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from redis.asyncio import Redis

bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_authorization_service(
    auth_client: Annotated[
        AuthServiceClient,
        Depends(get_auth_client),
    ],
    redis: Annotated[
        Redis,
        Depends(get_redis),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> AuthorizationService:
    """Создаёт сервис проверки прав."""
    return AuthorizationService(
        auth_client=auth_client,
        cache=RedisCache(redis),
        settings=settings,
    )


def require_permission(
    permission_code: str,
) -> Callable[..., Awaitable[None]]:
    """Создаёт dependency проверки permission."""

    async def dependency(
        request: Request,
        credentials: Annotated[
            HTTPAuthorizationCredentials | None,
            Depends(bearer_scheme),
        ],
        authorization_service: Annotated[
            AuthorizationService,
            Depends(get_authorization_service),
        ],
    ) -> None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="access_token_required",
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            )

        forwarded_headers = {}

        for header_name in (
            "User-Agent",
            "X-Request-ID",
            "X-Real-IP",
        ):
            header_value = request.headers.get(header_name)

            if header_value:
                forwarded_headers[header_name] = header_value

        try:
            has_permission = await authorization_service.has_permission(
                token=credentials.credentials,
                permission_code=permission_code,
                forwarded_headers=forwarded_headers,
            )
        except InvalidAccessTokenError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_access_token",
                headers={
                    "WWW-Authenticate": "Bearer",
                },
            ) from error
        except AuthUserForbiddenError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="user_forbidden",
            ) from error
        except AuthServiceContractError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="auth_service_unavailable",
            ) from error

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="permission_denied",
            )

    return dependency
