"""Внутренние эндпоинты получателей и аудитории уведомлений."""

from typing import Annotated
from uuid import UUID

from api.notification_dependencies import (
    get_notification_service,
    require_notification_api,
    require_notification_worker,
)
from api.v1.schemas.notification import (
    NotificationAudiencePageResponse,
    NotificationAudienceResponse,
    NotificationRecipientResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from services.exceptions import UserNotFoundError
from services.notification import (
    NotificationAudienceNotFoundError,
    NotificationService,
)

router = APIRouter(prefix="/internal/notifications", tags=["internal"])


@router.get(
    "/users/{user_id}",
    response_model=NotificationRecipientResponse,
    dependencies=[Depends(require_notification_worker)],
    summary="Получатель уведомления",
)
async def get_recipient(
    user_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRecipientResponse:
    """Возвращает email и ФИО активного пользователя для worker."""
    try:
        return await service.get_recipient(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "recipient_not_found"
        ) from exc


@router.post(
    "/audiences/{audience_id}",
    response_model=NotificationAudienceResponse,
    dependencies=[Depends(require_notification_api)],
    summary="Снимок аудитории рассылки",
)
async def create_audience(
    audience_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationAudienceResponse:
    """Идемпотентно сохраняет UUID активных пользователей."""
    return await service.create_audience(audience_id)


@router.get(
    "/audiences/{audience_id}",
    response_model=NotificationAudiencePageResponse,
    dependencies=[Depends(require_notification_api)],
    summary="Страница аудитории рассылки",
)
async def get_audience_page(
    audience_id: UUID,
    service: Annotated[NotificationService, Depends(get_notification_service)],
    after: UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> NotificationAudiencePageResponse:
    """Возвращает UUID следующей страницы без email и ФИО."""
    try:
        return await service.get_audience_page(audience_id, after, limit)
    except NotificationAudienceNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "audience_not_found"
        ) from exc
