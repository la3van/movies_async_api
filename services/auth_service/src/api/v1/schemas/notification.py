"""Схемы внутренних запросов сервисов уведомлений."""

from uuid import UUID

from pydantic import BaseModel


class NotificationRecipientResponse(BaseModel):
    """Данные получателя для формирования одного письма."""

    id: UUID
    email: str
    first_name: str | None
    last_name: str | None
    is_active: bool


class NotificationAudienceResponse(BaseModel):
    """Идентификатор сохранённого снимка аудитории."""

    audience_id: UUID


class NotificationAudiencePageResponse(BaseModel):
    """Страница UUID получателей без персональных данных."""

    users: list[UUID]
