"""Bounded request bodies, safe request IDs, and no caching of PII."""

import re
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class PrivacyMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = 16384) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        request_id = headers.get(b"x-request-id", b"").decode(
            "ascii", "ignore"
        )
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id):
            request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id

        async def safe_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-request-id", request_id.encode()),
                        (b"x-content-type-options", b"nosniff"),
                    ]
                )
            await send(message)

        messages: list[Message] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                await JSONResponse({"detail": "request_too_large"}, 413)(
                    scope, receive, safe_send
                )
                return
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay, safe_send)
