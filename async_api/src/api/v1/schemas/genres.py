"""Схемы API для жанры."""
from uuid import UUID
from pydantic import BaseModel, Field


class GenreResponse(BaseModel):
    """Модель ответа API для жанра."""

    uuid: UUID = Field(
        description='Уникальный идентификатор жанра',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    name: str = Field(
        description='Название жанра',
        examples=['Action', 'Comedy'],
    )
