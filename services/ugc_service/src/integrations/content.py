"""Проверка существования фильмов через Content Service."""

import logging
from uuid import UUID

import httpx
from cache.base import Cache
from core.config import get_settings
from core.exceptions import DependencyUnavailableError, FilmNotFoundError
from core.tracing import trace_method
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ContentServiceClient:
    """HTTP-клиент Content Service."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def film_exists(
        self,
        film_id: UUID,
        *,
        access_token: str,
        request_id: str,
    ) -> bool:
        try:
            response = await self._client.get(
                f"films/{film_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Request-ID": request_id,
                },
            )
        except httpx.RequestError as error:
            raise DependencyUnavailableError(
                "Content Service is unavailable"
            ) from error

        if response.status_code == 404:
            return False
        if response.status_code == 200:
            return True
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise DependencyUnavailableError(
                "Content Service is temporarily unavailable"
            )
        if response.status_code in {401, 403}:
            raise DependencyUnavailableError(
                "Content Service rejected internal validation request"
            )
        raise DependencyUnavailableError(
            f"Unexpected Content Service status: {response.status_code}"
        )

    async def close(self) -> None:
        await self._client.aclose()


class FilmCatalogService:
    """Проверить film_id с краткоживущим положительным кешем."""

    def __init__(
        self,
        client: ContentServiceClient,
        cache: Cache,
        *,
        enabled: bool,
        cache_ttl: int = 300,
    ) -> None:
        self._client = client
        self._cache = cache
        self._enabled = enabled
        self._cache_ttl = cache_ttl

    @trace_method("ugc.content.ensure_film_exists")
    async def ensure_exists(
        self,
        film_id: UUID,
        *,
        access_token: str,
        request_id: str,
    ) -> None:
        if not self._enabled:
            return

        cache_key = f"ugc:film_exists:{film_id}"
        try:
            if await self._cache.get(cache_key) == b"1":
                return
        except RedisError:
            logger.warning(
                "Unable to read film validation cache", exc_info=True
            )

        if not await self._client.film_exists(
            film_id,
            access_token=access_token,
            request_id=request_id,
        ):
            raise FilmNotFoundError

        try:
            await self._cache.set(cache_key, b"1", self._cache_ttl)
        except RedisError:
            logger.warning("Unable to cache film validation", exc_info=True)


content_client: ContentServiceClient | None = None


async def init_content_client() -> None:
    """Создать общий HTTP-клиент Content Service."""
    global content_client
    settings = get_settings()
    timeout = httpx.Timeout(
        connect=settings.content_service_connect_timeout,
        read=settings.content_service_read_timeout,
        write=settings.content_service_read_timeout,
        pool=settings.content_service_connect_timeout,
    )
    content_client = ContentServiceClient(
        httpx.AsyncClient(
            base_url=settings.content_service_base_url,
            timeout=timeout,
            follow_redirects=False,
        )
    )


async def close_content_client() -> None:
    """Закрыть общий HTTP-клиент."""
    global content_client
    if content_client is not None:
        await content_client.close()
    content_client = None


async def get_content_client() -> ContentServiceClient:
    """Вернуть инициализированный Content Service client."""
    if content_client is None:
        raise RuntimeError("Content Service client is not initialized")
    return content_client
