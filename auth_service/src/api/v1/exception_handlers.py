"""Обработчики исключений API v1."""
from fastapi import Request, status
from fastapi.responses import ORJSONResponse

from services.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    PermissionAlreadyExistsError,
    PermissionDeniedError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
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
