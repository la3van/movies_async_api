"""Ограничение частоты пользовательских событий через Redis."""
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from redis import Redis
from redis.exceptions import RedisError


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Результат проверки rate limit."""

    allowed: bool
    retry_after_seconds: int


class RateLimiterUnavailableError(Exception):
    """Redis rate limiter временно недоступен."""


class EventRateLimiter(Protocol):
    """Интерфейс rate limiter пользовательских событий."""
    def check(
        self,
        user_id: UUID,
    ) -> RateLimitDecision:
        """Проверить лимит пользователя."""
        ...

    def close(self) -> None:
        """Закрыть внешние ресурсы."""
        ...


class RedisEventRateLimiter:
    """Простой fixed-window rate limiter на Redis."""
    def __init__(
        self,
        *,
        redis: Redis,
        enabled: bool,
        key_prefix: str,
        requests: int,
        window_seconds: int,
    ) -> None:
        """Создать Redis rate limiter."""
        self._redis = redis
        self._enabled = enabled
        self._key_prefix = key_prefix
        self._requests = requests
        self._window_seconds = window_seconds

    def check(
        self,
        user_id: UUID,
    ) -> RateLimitDecision:
        """Увеличить счётчик пользователя и проверить лимит."""
        if not self._enabled:
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
            )

        key = f"{self._key_prefix}:{user_id}"

        try:
            with self._redis.pipeline(
                transaction=True,
            ) as pipe:
                pipe.set(key, 0, nx=True, ex=self._window_seconds)
                pipe.incr(key)
                pipe.ttl(key)

                results = pipe.execute()
        except RedisError as exc:
            raise RateLimiterUnavailableError(
                "Event rate limiter is unavailable"
            ) from exc

        current = int(results[1])
        ttl = max(int(results[2]), 1)

        if current <= self._requests:
            return RateLimitDecision(
                allowed=True,
                retry_after_seconds=0,
            )

        return RateLimitDecision(
            allowed=False,
            retry_after_seconds=ttl,
        )

    def close(self) -> None:
        """Закрыть Redis-клиент."""
        self._redis.close()
