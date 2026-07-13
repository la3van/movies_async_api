"""Базовые Pydantic-схемы API."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityResponse(BaseModel):
    """Базовая response-схема сущности из БД."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        description='Уникальный идентификатор сущности',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )

    created_at: datetime = Field(
        description='Дата и время создания записи',
        examples=['2026-01-01T12:00:00Z'],
    )
    updated_at: datetime = Field(
        description='Дата и время последнего обновления записи',
        examples=['2026-01-01T12:00:00Z'],
    )
