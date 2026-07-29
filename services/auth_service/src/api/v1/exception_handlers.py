"""Обработчики исключений API v1."""
from fastapi import Request, status
from fastapi.responses import ORJSONResponse

from services.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidOAuthStateError,
    InvalidRefreshTokenError,
    OAuthProviderNotConfiguredError,
    OAuthProviderResponseError,
    OAuthProviderUnavailableError,
    OAuthStateStorageError,
    PermissionAlreadyExistsError,
    PermissionDeniedError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    OAuthAccountLinkRequiredError,
    OAuthAuthorizationError,
    OAuthEmailRequiredError,
    InvalidLoginHistoryDateRangeError,
)


EXCEPTION_STATUS_CODES: dict[type[Exception], int] = {
    UserAlreadyExistsError: status.HTTP_409_CONFLICT,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InactiveUserError: status.HTTP_403_FORBIDDEN,
    InvalidRefreshTokenError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    RoleAlreadyExistsError: status.HTTP_409_CONFLICT,
    RoleNotFoundError: status.HTTP_404_NOT_FOUND,
    PermissionAlreadyExistsError: status.HTTP_409_CONFLICT,
    PermissionNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidOAuthStateError: status.HTTP_400_BAD_REQUEST,
    OAuthProviderNotConfiguredError: status.HTTP_503_SERVICE_UNAVAILABLE,
    OAuthProviderUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
    OAuthProviderResponseError: status.HTTP_502_BAD_GATEWAY,
    OAuthStateStorageError: status.HTTP_503_SERVICE_UNAVAILABLE,
    OAuthAuthorizationError: status.HTTP_400_BAD_REQUEST,
    OAuthEmailRequiredError: status.HTTP_400_BAD_REQUEST,
    OAuthAccountLinkRequiredError: status.HTTP_409_CONFLICT,
    InvalidLoginHistoryDateRangeError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


async def service_exception_handler(
    request: Request,
    exc: Exception,
) -> ORJSONResponse:
    """Преобразует сервисное исключение в HTTP-ответ."""
    status_code = EXCEPTION_STATUS_CODES[type(exc)]

    return ORJSONResponse(
        status_code=status_code,
        content={
            'detail': str(exc),
        },
    )
