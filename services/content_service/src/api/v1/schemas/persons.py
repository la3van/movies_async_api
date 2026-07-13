"""Схемы API для персон."""
from uuid import UUID
from pydantic import BaseModel, Field


class PersonFilmResponse(BaseModel):
    """Фильм внутри информации о персоне."""

    uuid: UUID = Field(
        description='Уникальный идентификатор персоны',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    roles: list[str] = Field(
        description='Список ролей персоны',
        examples=[['actor'], ['actor, director, writer']],
    )


class PersonResponse(BaseModel):
    """Модель ответа API для персоны."""

    uuid: UUID = Field(
        description='Уникальный идентификатор персоны',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    full_name: str = Field(
        description='Имя персоны',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    )
    films: list[PersonFilmResponse] = Field(
        description='Список фильмов с участием персоны',
    )
