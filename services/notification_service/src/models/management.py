"""Контракты шаблонов, рассылок и входящих событий."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, field_validator

from models.contract import ClosedModel, CreateNotification


class TemplateInput(ClosedModel):
    """Содержимое новой версии текстового или HTML-шаблона."""

    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    body_format: Literal["text", "html"] = "text"

    @field_validator("subject", "body")
    @classmethod
    def validate_content(cls, value: str) -> str:
        """Проверяет синтаксис содержимого новой версии шаблона."""
        from services.rendering import validate_template

        validate_template(value)
        return value


class TemplateCreate(TemplateInput):
    """Содержимое и уникальное имя создаваемого шаблона."""

    name: str = Field(
        min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$"
    )


class CampaignInput(ClosedModel):
    """Запрос рассылки с версией шаблона и временем начала."""

    template_id: UUID
    version: int | None = Field(default=None, ge=1)
    context: dict[str, str] = Field(default_factory=dict, max_length=32)
    scheduled_at: AwareDatetime | None = None

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: dict[str, str]) -> dict[str, str]:
        """Проверяет допустимые переменные контекста рассылки."""
        return CreateNotification.check_context(value)


class DeliveryResult(ClosedModel):
    """Результат конкретной попытки отправки уведомления."""

    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    event_id: UUID
    delivery_id: UUID
    notification_id: UUID
    status: Literal["retry", "sent", "failed"]
    attempt: StrictInt = Field(ge=1)
    error_code: str | None = Field(default=None, max_length=100)


class CinemaEvent(ClosedModel):
    """Событие регистрации пользователя или появления фильма."""

    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    event_id: UUID
    kind: Literal["user.registered", "film.created"]
    aggregate_id: UUID
    occurred_at: AwareDatetime
    title: str | None = Field(default=None, max_length=2000)
