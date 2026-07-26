"""Middleware для обработки X-Request-ID."""
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)


class RequestIdMiddleware:
    """Сохраняет или создает X-Request-ID для HTTP-запроса."""
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_headers = MutableHeaders(scope=scope)

        request_id = (
            request_headers.get("x-request-id", "").strip()
        )

        if not request_id or len(request_id) > 128:
            request_id = uuid4().hex

        request_headers["x-request-id"] = request_id

        async def send_with_request_id(
            message: Message,
        ) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(
                    scope=message,
                )
                response_headers["x-request-id"] = request_id

            await send(message)

        await self._app(
            scope,
            receive,
            send_with_request_id,
        )
