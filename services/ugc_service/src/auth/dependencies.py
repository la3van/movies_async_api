"""FastAPI dependencies аутентификации."""

from typing import Annotated

from auth.client import AuthServiceClient, get_auth_client
from auth.exceptions import (
    AuthServiceContractError,
    AuthServiceUnavailableError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from auth.models import AuthenticatedUser
from auth.service import AuthenticationService
from core.config import Settings, get_settings
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


def get_authentication_service(
    client: Annotated[AuthServiceClient, Depends(get_auth_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthenticationService:
    """Собрать сервис аутентификации."""
    return AuthenticationService(client, settings)


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    service: Annotated[
        AuthenticationService,
        Depends(get_authentication_service),
    ],
) -> AuthenticatedUser:
    """Вернуть текущего активного пользователя."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="access_token_required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    forwarded_headers = {
        name: value
        for name in ("User-Agent", "X-Request-ID", "X-Real-IP")
        if (value := request.headers.get(name))
    }
    try:
        return await service.authenticate(
            token=credentials.credentials,
            forwarded_headers=forwarded_headers,
        )
    except InvalidAccessTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_access_token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    except AuthUserForbiddenError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="user_forbidden",
        ) from error
    except (AuthServiceUnavailableError, AuthServiceContractError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="auth_service_unavailable",
        ) from error
