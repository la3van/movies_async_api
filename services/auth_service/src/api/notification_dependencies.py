"""Зависимости внутренних методов уведомлений."""

import secrets
from typing import Annotated

from api.dependencies import get_uow_factory
from core.config import get_settings
from fastapi import Depends, Header, HTTPException, status
from services.notification import NotificationService
from unit_of_work.base import UnitOfWorkFactory


def verify_service_token(provided: str, expected: str) -> None:
    """Отклоняет пустой или неверный ключ межсервисного доступа."""
    if not expected or not secrets.compare_digest(
        provided.encode(), expected.encode()
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid_service_token")


async def require_notification_worker(
    x_service_token: Annotated[str, Header()],
) -> None:
    """Разрешает worker получать данные одного адресата."""
    verify_service_token(
        x_service_token,
        get_settings().notification_worker_token.get_secret_value(),
    )


async def require_notification_api(
    x_service_token: Annotated[str, Header()],
) -> None:
    """Разрешает Notification API работать со снимками аудитории."""
    verify_service_token(
        x_service_token,
        get_settings().notification_api_token.get_secret_value(),
    )


def get_notification_service(
    uow_factory: Annotated[UnitOfWorkFactory, Depends(get_uow_factory)],
) -> NotificationService:
    """Создаёт сервис уведомлений с общей фабрикой UoW."""
    return NotificationService(uow_factory)
