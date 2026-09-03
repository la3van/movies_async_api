"""Сервис авторизации Content Service."""

import hashlib
import logging

from auth.client import AuthServiceClient
from auth.exceptions import AuthServiceUnavailableError
from auth.jwt import decode_access_token
from auth.models import PermissionDecision
from cache.base import Cache
from core.config import Settings
from pydantic import ValidationError
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Проверяет права пользователя с graceful degradation."""

    def __init__(
        self,
        auth_client: AuthServiceClient,
        cache: Cache,
        settings: Settings,
    ) -> None:
        self._auth_client = auth_client
        self._cache = cache
        self._settings = settings

    async def has_permission(
        self,
        token: str,
        permission_code: str,
        forwarded_headers: dict[str, str],
    ) -> bool:
        """
        Проверяет право пользователя.

        При нормальной работе источником истины является Auth Service.
        При его отказе используются проверенные JWT claims.
        """
        claims = decode_access_token(
            token=token,
            settings=self._settings,
        )

        cache_key = self._build_cache_key(
            token=token,
            permission_code=permission_code,
        )

        cached_decision = await self._get_cached_decision(
            cache_key,
        )
        if cached_decision is not None:
            return cached_decision.has_permission

        try:
            has_permission = await self._auth_client.check_permission(
                token=token,
                permission_code=permission_code,
                forwarded_headers=forwarded_headers,
            )
        except AuthServiceUnavailableError:
            logger.warning(
                (
                    "Auth Service is unavailable. "
                    "Using access token claims as fallback."
                ),
                exc_info=True,
            )

            return claims.is_superuser or permission_code in claims.permissions

        await self._cache_decision(
            key=cache_key, has_permission=has_permission
        )

        return has_permission

    async def _get_cached_decision(
        self,
        key: str,
    ) -> PermissionDecision | None:
        """Безопасно получает решение из Redis."""
        try:
            return await self._cache.get_model(
                key=key,
                model_type=PermissionDecision,
            )
        except (
            RedisError,
            ValidationError,
            ValueError,
        ):
            logger.warning(
                "Unable to read permission decision from Redis.",
                exc_info=True,
            )
            return None

    async def _cache_decision(
        self,
        key: str,
        has_permission: bool,
    ) -> None:
        """Безопасно сохраняет состояние в Redis."""
        try:
            await self._cache.set_model(
                key=key,
                value=PermissionDecision(
                    has_permission=has_permission,
                ),
                ttl=self._settings.auth_permission_cache_ttl,
            )
        except RedisError:
            logger.warning(
                "Unable to cache permission decision.",
                exc_info=True,
            )

    @staticmethod
    def _build_cache_key(
        token: str,
        permission_code: str,
    ) -> str:
        """Создаёт кеш-ключ без сохранения JWT в открытом виде."""
        token_hash = hashlib.sha256(
            token.encode("utf-8"),
        ).hexdigest()

        return f"auth:permission:{token_hash}:{permission_code}"
