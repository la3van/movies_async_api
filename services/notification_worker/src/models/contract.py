"""Контракт v1 для передачи заданий без персональных данных адресата."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator


class ClosedModel(BaseModel):
    """Неизменяемая модель, запрещающая неизвестные поля."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class TemplateSnapshot(ClosedModel):
    """Снимок конкретной версии шаблона для задания."""

    template_id: UUID
    version: Annotated[StrictInt, Field(ge=1)]
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=50000)
    body_format: Literal["text", "html"] = "text"

    @field_validator("subject", "body")
    @classmethod
    def check_template(cls, value: str) -> str:
        """Проверяет допустимый синтаксис подстановок шаблона."""
        from services.rendering import validate_template

        validate_template(value)
        return value


class TraceContext(ClosedModel):
    """Идентификатор запроса и переносимый контекст трассировки."""

    request_id: str = Field(min_length=1, max_length=128)
    traceparent: str | None = Field(
        default=None,
        pattern=r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$",
    )


class CreateNotification(ClosedModel):
    """Запрос персонального уведомления без данных адресата."""

    user_id: UUID
    channel: Literal["email"] = "email"
    template: TemplateSnapshot
    context: dict[str, str] = Field(default_factory=dict, max_length=32)

    @field_validator("context")
    @classmethod
    def check_context(cls, value: dict[str, str]) -> dict[str, str]:
        """Ограничивает контекст и запрещает подмену данных получателя."""
        import re

        for key, item in value.items():
            if (
                not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key)
                or key in {"email", "first_name", "last_name"}
                or len(item) > 2000
            ):
                raise ValueError("Invalid context field")
        return value


class DeliveryJob(CreateNotification):
    """Версионированное задание доставки для передачи через Kafka."""

    schema_version: Annotated[StrictInt, Field(ge=1, le=1)] = 1
    event_id: UUID
    delivery_id: UUID
    notification_id: UUID
    trace_context: TraceContext


class Accepted(ClosedModel):
    """Подтверждение приёма заявки с устойчивыми идентификаторами."""

    notification_id: UUID
    delivery_id: UUID
    status: Literal["accepted"] = "accepted"
