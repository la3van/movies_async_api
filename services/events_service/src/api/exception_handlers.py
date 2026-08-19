"""Глобальные обработчики HTTP-ошибок."""
from http import HTTPStatus

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from core.request_id import get_request_id


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
