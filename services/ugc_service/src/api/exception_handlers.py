"""Единый формат ожидаемых и неожиданных HTTP-ошибок."""

import logging

from core.exceptions import (
    DependencyUnavailableError,
    EntityNotFoundError,
    ResourceConflictError,
    ResourceForbiddenError,
)
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    """Зарегистрировать глобальные exception handlers."""

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request, error: HTTPException
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=error.status_code,
            content={
                "detail": error.detail,
                "request_id": _request_id(request),
            },
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> ORJSONResponse:
        errors = [
            {
                "loc": [str(part) for part in item["loc"]],
                "msg": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "validation_error",
                "request_id": _request_id(request),
                "errors": errors,
            },
        )

    @app.exception_handler(EntityNotFoundError)
    async def handle_not_found(
        request: Request, error: EntityNotFoundError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": error.detail,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(ResourceConflictError)
    async def handle_conflict(
        request: Request, error: ResourceConflictError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": error.detail,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(ResourceForbiddenError)
    async def handle_forbidden(
        request: Request, error: ResourceForbiddenError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": error.detail,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(DependencyUnavailableError)
    async def handle_dependency_unavailable(
        request: Request, error: DependencyUnavailableError
    ) -> ORJSONResponse:
        logger.warning("UGC dependency unavailable", exc_info=True)
        return ORJSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "detail": error.detail,
                "request_id": _request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(
        request: Request, error: Exception
    ) -> ORJSONResponse:
        logger.exception("Unhandled UGC Service error")
        return ORJSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "internal_server_error",
                "request_id": _request_id(request),
            },
        )
