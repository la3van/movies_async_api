"""Liveness и readiness endpoints."""

from collections.abc import Awaitable
from typing import cast

from db.mongo import mongo_is_ready
from db.redis import get_redis
from fastapi import APIRouter, Response, status

router = APIRouter(tags=["Состояние сервиса"])


@router.get("/health", summary="Проверка процесса")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Проверка готовности зависимостей")
async def ready(response: Response) -> dict[str, object]:
    mongo_ready = await mongo_is_ready()
    redis_ready = False
    try:
        redis = await get_redis()
        redis_ready = await cast(
            Awaitable[bool],
            redis.ping(),
        )
    except Exception:
        redis_ready = False

    ready_state = mongo_ready and redis_ready
    if not ready_state:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready_state else "not_ready",
        "dependencies": {"mongodb": mongo_ready, "redis": redis_ready},
    }
