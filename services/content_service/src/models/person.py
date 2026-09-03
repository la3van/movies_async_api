"""Модуль с описанием Pydantic модели персоны."""

from pydantic import BaseModel, ConfigDict, Field


class PersonFilm(BaseModel):
    """Схема фильма, связанного с персоной."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    roles: list[str] = Field(default_factory=list)


class Person(BaseModel):
    """Схема персоны из Elasticsearch."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    full_name: str
    films: list[PersonFilm] = Field(default_factory=list)
