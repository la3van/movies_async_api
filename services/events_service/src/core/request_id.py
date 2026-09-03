"""Работа с идентификатором HTTP-запроса."""

from uuid import uuid4

from flask import Flask, g, request

REQUEST_ID_HEADER = "X-Request-ID"
MAX_REQUEST_ID_LENGTH = 128


def get_request_id() -> str:
    """Получить идентификатор текущего HTTP-запроса."""
    return getattr(
        g,
        "request_id",
        "",
    )


def register_request_id(
    app: Flask,
) -> None:
    """Зарегистрировать обработку заголовка X-Request-ID."""

    @app.before_request
    def set_request_id() -> None:
        request_id = request.headers.get(
            REQUEST_ID_HEADER,
            "",
        ).strip()

        if not request_id or len(request_id) > MAX_REQUEST_ID_LENGTH:
            request_id = uuid4().hex

        g.request_id = request_id

    @app.after_request
    def add_request_id(response):
        response.headers[REQUEST_ID_HEADER] = get_request_id()

        return response
