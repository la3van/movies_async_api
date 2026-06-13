"""Схемы API для персон."""
from uuid import UUID

from pydantic import BaseModel


class PersonFilmResponse(BaseModel):
    """Фильм внутри информации о персоне."""

    uuid: UUID
    roles: list[str]


class PersonResponse(BaseModel):
    """Модель ответа API для персоны."""

    uuid: UUID
    full_name: str
    films: list[PersonFilmResponse]
