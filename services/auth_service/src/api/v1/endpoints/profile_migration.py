"""Authenticated internal migration endpoints with bounded batches."""

from typing import Annotated
from uuid import UUID

from api.dependencies import get_redis_cache, get_uow_factory
from api.notification_dependencies import verify_service_token
from api.v1.schemas.profile_migration import LegacyProfile, LegacyProfileBatch
from cache.base import Cache
from core.config import get_settings
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from services.profile_migration import ProfileMigrationService
from unit_of_work.base import UnitOfWorkFactory


def require_migration(x_service_token: Annotated[str, Header()] = "") -> None:
    settings = get_settings()
    verify_service_token(
        x_service_token, settings.profile_migration_token.get_secret_value()
    )
    if not settings.profile_names_external:
        raise HTTPException(
            409, "enable_profile_names_external_before_migration"
        )


router = APIRouter(
    prefix="/internal/profile-migration",
    dependencies=[Depends(require_migration)],
    tags=["internal"],
)


def get_service(
    uow: Annotated[UnitOfWorkFactory, Depends(get_uow_factory)],
    cache: Annotated[Cache, Depends(get_redis_cache)],
) -> ProfileMigrationService:
    return ProfileMigrationService(uow, cache)


@router.get("/", response_model=list[LegacyProfile])
async def list_names(
    response: Response,
    service: Annotated[ProfileMigrationService, Depends(get_service)],
    after: UUID | None = None,
    limit: int = Query(100, ge=1, le=100),
) -> list[LegacyProfile]:
    response.headers["Cache-Control"] = "no-store"
    return await service.list_profiles(after, limit)


@router.post("/clear")
async def clear_names(
    data: LegacyProfileBatch,
    service: Annotated[ProfileMigrationService, Depends(get_service)],
) -> dict[str, int]:
    return {"cleared": await service.clear(data.items)}
