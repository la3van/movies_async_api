"""Redis-хранилище отозванных access-токенов."""

from collections.abc import Sequence
from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError
from services.exceptions import (
    AccessTokenRevocationStorageError,
)
from token_revocation.base import (
    AccessTokenRevocationStore,
)


class RedisAccessTokenRevocationStore(
    AccessTokenRevocationStore,
):
    """Хранит признаки отзыва access-токенов в Redis."""

    def __init__(
        self,
        *,
        redis: Redis,
        key_prefix: str,
        session_ttl_seconds: int,
        clock_skew_seconds: int = 30,
    ) -> None:
        """Инициализирует Redis-хранилище."""
        if not key_prefix:
            raise ValueError(
                "Access token revocation key prefix is empty",
            )
        if session_ttl_seconds < 1:
            raise ValueError(
                "Session revocation TTL must be positive",
            )
        if clock_skew_seconds < 0:
            raise ValueError(
                "Clock skew must not be negative",
            )

        self._redis = redis
        self._key_prefix = key_prefix
        self._session_ttl_seconds = session_ttl_seconds
        self._clock_skew_seconds = clock_skew_seconds

    async def revoke_token(
        self,
        token_id: UUID,
        expires_at: datetime,
    ) -> None:
        """Отзывает один access-токен до его истечения."""
        now = datetime.now(timezone.utc)

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        remaining_seconds = ceil(
            (expires_at - now).total_seconds(),
        )
        if remaining_seconds <= 0:
            return

        ttl_seconds = remaining_seconds + self._clock_skew_seconds

        try:
            await self._redis.set(
                name=self._build_token_key(token_id),
                value="1",
                ex=ttl_seconds,
            )
        except RedisError as error:
            raise AccessTokenRevocationStorageError(
                "Could not revoke access token",
            ) from error

    async def revoke_sessions(
        self,
        session_ids: Sequence[UUID],
    ) -> None:
        """Отзывает access-токены указанных сессий."""
        unique_session_ids = set(session_ids)
        if not unique_session_ids:
            return

        try:
            async with self._redis.pipeline(
                transaction=False,
            ) as pipeline:
                for session_id in unique_session_ids:
                    pipeline.set(
                        name=self._build_session_key(
                            session_id,
                        ),
                        value="1",
                        ex=(
                            self._session_ttl_seconds
                            + self._clock_skew_seconds
                        ),
                    )

                await pipeline.execute()
        except RedisError as error:
            raise AccessTokenRevocationStorageError(
                "Could not revoke access token sessions",
            ) from error

    async def is_revoked(
        self,
        token_id: UUID,
        session_id: UUID,
    ) -> bool:
        """Проверяет отзыв токена и его сессии."""
        try:
            values = await self._redis.mget(
                [
                    self._build_token_key(token_id),
                    self._build_session_key(session_id),
                ],
            )
        except RedisError as error:
            raise AccessTokenRevocationStorageError(
                "Could not check access token revocation",
            ) from error

        return any(value is not None for value in values)

    def _build_token_key(
        self,
        token_id: UUID,
    ) -> str:
        """Формирует ключ конкретного токена."""
        return f"{self._key_prefix}:jti:{token_id}"

    def _build_session_key(
        self,
        session_id: UUID,
    ) -> str:
        """Формирует ключ сессии."""
        return f"{self._key_prefix}:sid:{session_id}"
