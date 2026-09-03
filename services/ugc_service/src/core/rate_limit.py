"""Точечное ограничение количества запросов через Redis."""

import logging
from collections.abc import Awaitable, Callable
from hashlib import sha256
from ipaddress import ip_address
from time import time
from typing import Annotated, Any, cast

from core.config import get_settings
from db.redis import get_redis
from fastapi import Depends, HTTPException, Request, Response, status
from opentelemetry import trace
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end
return {current, ttl}
"""

RateLimitDependency = Callable[..., Awaitable[None]]


def rate_limit(
    *, scope: str, requests: int, window_seconds: int
) -> RateLimitDependency:
    """Создать dependency с фиксированным окном для endpoint."""
    if not scope or requests < 1 or window_seconds < 1:
        raise ValueError("Invalid rate limit configuration")

    async def dependency(
        request: Request,
        response: Response,
        redis: Annotated[Redis, Depends(get_redis)],
    ) -> None:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        client_hash = sha256(_get_client_ip(request).encode()).hexdigest()
        key = f"{settings.rate_limit_key_prefix}:{scope}:{client_hash}"
        span = trace.get_current_span()

        try:
            result = await cast(
                Awaitable[Any],
                redis.eval(RATE_LIMIT_SCRIPT, 1, key, window_seconds),
            )
            if not isinstance(result, (list, tuple)) or len(result) != 2:
                raise ValueError("Unexpected Redis response")
            current, ttl = int(result[0]), max(int(result[1]), 1)
        except (RedisError, RuntimeError, TypeError, ValueError):
            logger.warning(
                "Rate limiter unavailable; allowing request", exc_info=True
            )
            span.set_attribute("rate_limit.available", False)
            return

        remaining = max(requests - current, 0)
        headers = {
            "X-RateLimit-Limit": str(requests),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time()) + ttl),
        }
        span.set_attribute("rate_limit.available", True)
        span.set_attribute("rate_limit.scope", scope)
        span.set_attribute("rate_limit.allowed", current <= requests)

        if current > requests:
            headers["Retry-After"] = str(ttl)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limit_exceeded",
                headers=headers,
            )

        for name, value in headers.items():
            response.headers[name] = value

    return dependency


def _get_client_ip(request: Request) -> str:
    for raw_value in (
        request.headers.get("x-real-ip"),
        (request.headers.get("x-forwarded-for") or "").split(",", 1)[0],
        request.client.host if request.client else None,
    ):
        if not raw_value:
            continue
        try:
            return str(ip_address(raw_value.strip()))
        except ValueError:
            continue
    return "unknown"
