"""Глобальные обработчики HTTP-ошибок."""
import logging
from http import HTTPStatus

from flask import Flask, jsonify
from werkzeug.exceptions import (
    HTTPException,
    RequestEntityTooLarge,
)

from core.request_id import get_request_id

logger = logging.getLogger(__name__)


def register_exception_handlers(
    app: Flask,
) -> None:
    """Зарегестрировать глобальные обработчики HTTP-ошибок."""
    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(
        error: RequestEntityTooLarge,
    ):
        """Обработать превышение допустимого размера запроса."""
        return (
            jsonify(
                {
                    "detail": "request_entity_too_large",
                    "request_id": get_request_id()
                }
            ),
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(
        error: HTTPException,
    ):
        """Преобразовать стандартную HTTP-ошибку Flask в JSON."""
        status_code = (
            error.code
            or HTTPStatus.INTERNAL_SERVER_ERROR
        )

        return (
            jsonify(
                {
                    "detail": (
                        error.name.lower().replace(" ", "-")
                    ),
                    "request_id": get_request_id(),
                }
            ),
            status_code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(
        error: Exception,
    ):
        """Обработать неожиданную внутреннюю ошибку сервиса."""
        logger.exception(
            "Необработанная ошибка events-service",
        )

        return (
            jsonify(
                {
                    "detail": "internal_server_error",
                    "request_id": get_request_id(),
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
