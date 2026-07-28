"""Точечное ограничение количества запросов через Redis."""
import logging
from collections.abc import Awaitable, Callable
from hashlib import sha256
from ipaddress import ip_address
from time import time
from typing import Annotated

from fastapi import (
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from opentelemetry import trace
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.config import get_settings
from db.redis import get_redis

logger = logging.getLogger(__name__)


RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])

if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end

local ttl = redis.call('TTL', KEYS[1])

if ttl < 0 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end

return {current, ttl}
"""


RateLimitDependency = Callable[..., Awaitable[None]]


def rate_limit(
    *,
    scope: str,
    requests: int,
    window_seconds: int,
) -> RateLimitDependency:
    """Создаёт dependency с лимитом для конкретного endpoint."""
    if not scope:
        raise ValueError('Rate limit scope must not be empty')

    if requests < 1:
        raise ValueError(
            'Rate limit requests must be greater than zero',
        )

    if window_seconds < 1:
        raise ValueError(
            'Rate limit window must be greater than zero',
        )

    async def dependency(
        request: Request,
        response: Response,
        redis: Annotated[
            Redis,
            Depends(get_redis),
        ],
    ) -> None:
        settings = get_settings()

        if not settings.rate_limit_enabled:
            return

        client_ip = _get_client_ip(request)
        client_hash = sha256(
            client_ip.encode('utf-8'),
        ).hexdigest()

        redis_key = (
            f'{settings.rate_limit_key_prefix}:'
            f'{scope}:{client_hash}'
        )

        span = trace.get_current_span()

        try:
            result = await redis.eval(
                RATE_LIMIT_SCRIPT,
                1,
                redis_key,
                window_seconds,
            )

            if not isinstance(result, (list, tuple)):
                raise ValueError(
                    'Unexpected Redis rate limit response',
                )

            if len(result) != 2:
                raise ValueError(
                    'Unexpected Redis rate limit response length',
                )

            current_requests = int(result[0])
            ttl = max(int(result[1]), 1)
        except (
            RedisError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            logger.warning(
                (
                    'Rate limiter is unavailable. '
                    'The request is allowed.'
                ),
                exc_info=True,
            )

            span.set_attribute(
                'rate_limit.available',
                False,
            )
            span.set_attribute(
                'rate_limit.scope',
                scope,
            )

            return

        remaining = max(
            requests - current_requests,
            0,
        )

        reset_at = int(time()) + ttl
        allowed = current_requests <= requests

        headers = {
            'X-RateLimit-Limit': str(requests),
            'X-RateLimit-Remaining': str(remaining),
            'X-RateLimit-Reset': str(reset_at),
        }

        span.set_attribute(
            'rate_limit.available',
            True,
        )
        span.set_attribute(
            'rate_limit.scope',
            scope,
        )
        span.set_attribute(
            'rate_limit.limit',
            requests,
        )
        span.set_attribute(
            'rate_limit.current',
            current_requests,
        )
        span.set_attribute(
            'rate_limit.remaining',
            remaining,
        )
        span.set_attribute(
            'rate_limit.allowed',
            allowed,
        )

        if not allowed:
            headers['Retry-After'] = str(ttl)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='rate_limit_exceeded',
                headers=headers,
            )

        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

    return dependency


def _get_client_ip(request: Request) -> str:
    """Определяет исходный IP клиента."""
    real_ip = _normalize_ip(
        request.headers.get('x-real-ip'),
    )
    if real_ip is not None:
        return real_ip

    forwarded_for = request.headers.get(
        'x-forwarded-for',
    )
    if forwarded_for:
        first_forwarded_ip = forwarded_for.split(
            ',',
            maxsplit=1,
        )[0].strip()

        normalized_forwarded_ip = _normalize_ip(
            first_forwarded_ip,
        )
        if normalized_forwarded_ip is not None:
            return normalized_forwarded_ip

    if request.client is not None:
        client_ip = _normalize_ip(
            request.client.host,
        )
        if client_ip is not None:
            return client_ip

    return 'unknown'


def _normalize_ip(value: str | None) -> str | None:
    """Проверяет и нормализует IPv4 или IPv6."""
    if not value:
        return None

    try:
        return str(
            ip_address(value.strip()),
        )
    except ValueError:
        return None
