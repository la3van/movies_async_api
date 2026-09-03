"""Ограничение размера HTTP-запроса."""

from http import HTTPStatus

import orjson
from starlette.types import ASGIApp, Receive, Scope, Send


class RequestSizeLimitMiddleware:
    """Отклонить заведомо слишком большой запрос по Content-Length."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self._app = app
        self._max_bytes = max_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            raw_length = headers.get(b"content-length")
            if raw_length is not None:
                try:
                    content_length = int(raw_length)
                except ValueError:
                    content_length = 0
                if content_length > self._max_bytes:
                    body = orjson.dumps({"detail": "request_entity_too_large"})
                    await send(
                        {
                            "type": "http.response.start",
                            "status": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            "headers": [
                                (b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode()),
                            ],
                        }
                    )
                    await send({"type": "http.response.body", "body": body})
                    return

        await self._app(scope, receive, send)
