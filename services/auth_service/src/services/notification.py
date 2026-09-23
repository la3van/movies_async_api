"""Сервис внутренних сценариев уведомлений."""

from uuid import UUID

from api.v1.schemas.notification import (
    NotificationAudiencePageResponse,
    NotificationAudienceResponse,
    NotificationRecipientResponse,
)
from services.exceptions import AuthServiceError, UserNotFoundError
from unit_of_work.base import UnitOfWorkFactory


class NotificationAudienceNotFoundError(AuthServiceError):
    """Запрошенный снимок аудитории отсутствует."""


class NotificationService:
    """Предоставляет данные получателя и фиксированную аудиторию."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Сохраняет фабрику транзакций Auth."""
        self._uow_factory = uow_factory

    async def get_recipient(
        self, user_id: UUID
    ) -> NotificationRecipientResponse:
        """Возвращает актуальные данные только активного получателя."""
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None or not user.is_active:
                raise UserNotFoundError("Recipient not found")
            return NotificationRecipientResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
            )

    async def create_audience(
        self, audience_id: UUID
    ) -> NotificationAudienceResponse:
        """Фиксирует снимок аудитории в одной транзакции."""
        async with self._uow_factory() as uow:
            await uow.notification_audiences.create_snapshot(audience_id)
            await uow.commit()
        return NotificationAudienceResponse(audience_id=audience_id)

    async def get_audience_page(
        self,
        audience_id: UUID,
        after: UUID | None,
        limit: int,
    ) -> NotificationAudiencePageResponse:
        """Возвращает страницу ранее сохранённого снимка."""
        async with self._uow_factory() as uow:
            users = await uow.notification_audiences.get_page(
                audience_id, after, limit
            )
            if users is None:
                raise NotificationAudienceNotFoundError("Audience not found")
        return NotificationAudiencePageResponse(users=users)
