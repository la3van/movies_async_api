"""Self-service CRUD and read-only staff endpoints."""

from typing import Annotated
from uuid import UUID

from api.dependencies import (
    get_current_user,
    get_service,
    require_notification_worker,
    require_reader,
)
from api.v1.schemas.profiles import (
    NotificationName,
    ProfileCreate,
    ProfilePage,
    ProfileResponse,
    ProfileUpdate,
)
from auth.client import CurrentUser
from fastapi import APIRouter, Depends, Query, Request, Response
from services.profile import ProfileService

router = APIRouter(prefix="/profiles", tags=["Profiles"])
internal_router = APIRouter(prefix="/internal/profiles", tags=["Internal"])
Service = Annotated[ProfileService, Depends(get_service)]
User = Annotated[CurrentUser, Depends(get_current_user)]
Reader = Annotated[CurrentUser, Depends(require_reader)]


@router.post("/me", response_model=ProfileResponse, status_code=201)
async def create_profile(
    data: ProfileCreate, request: Request, user: User, service: Service
) -> ProfileResponse:
    return await service.create(user.id, data, request.state.request_id)


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    request: Request, user: User, service: Service
) -> ProfileResponse:
    return await service.get(user.id, user.id, request.state.request_id)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdate, request: Request, user: User, service: Service
) -> ProfileResponse:
    return await service.update(user.id, data, request.state.request_id)


@router.delete("/me", status_code=204)
async def delete_profile(
    request: Request, user: User, service: Service
) -> Response:
    await service.delete(user.id, request.state.request_id)
    return Response(status_code=204)


@router.get("/", response_model=ProfilePage)
async def list_profiles(
    request: Request,
    user: Reader,
    service: Service,
    after: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
) -> ProfilePage:
    return await service.list(user.id, after, limit, request.state.request_id)


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_staff_profile(
    user_id: UUID, request: Request, user: Reader, service: Service
) -> ProfileResponse:
    return await service.get(
        user_id, user.id, request.state.request_id, action="profile.staff_read"
    )


@internal_router.get(
    "/{user_id}/notification-name",
    response_model=NotificationName,
    dependencies=[Depends(require_notification_worker)],
)
async def notification_name(
    user_id: UUID, request: Request, service: Service
) -> NotificationName:
    profile = await service.get(
        user_id,
        UUID(int=0),
        request.state.request_id,
        action="profile.notification_read",
    )
    return NotificationName(
        user_id=user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
    )
