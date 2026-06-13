"""Схемы API для жанры."""
from uuid import UUID
from pydantic import BaseModel


class GenreResponse(BaseModel):
    """Модель ответа API для жанра."""

    uuid: UUID
    name: str
