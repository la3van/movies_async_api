"""Модуль с описанием Pydantic модели фильма."""

from models.genre import Genre
from pydantic import BaseModel, ConfigDict, Field


class FilmPerson(BaseModel):
    """Персона, связанная с фильмом."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    full_name: str


class ShortFilm(BaseModel):
    """Кратка информация о фильме для списков и поиска."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    title: str
    imdb_rating: float | None = None


class Film(BaseModel):
    """Полная информация о фильме."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    title: str
    imdb_rating: float | None = None
    description: str | None

    genre: list[Genre] = Field(default_factory=list)
    actors: list[FilmPerson] = Field(default_factory=list)
    writers: list[FilmPerson] = Field(default_factory=list)
    directors: list[FilmPerson] = Field(default_factory=list)
