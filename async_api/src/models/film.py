"""Модуль с описанием Pydantic модели фильма."""
from pydantic import BaseModel, ConfigDict, Field

from models.genre import Genre


class FilmPerson(BaseModel):
    """Персона, связанная с фильмом."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    full_name: str


class ShortFilm(BaseModel):
    """Кратка информация о фильме для списков и поиска."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    title: str
    imdb_rating: float | None = None


class Film(BaseModel):
    """Полная информация о фильме."""
    model_config = ConfigDict(extra='forbid')

    uuid: str  # noqa: A003, VNE003
    title: str
    imdb_rating: float | None = None
    description: str | None

    genre: list[Genre] = Field(default_factory=list)
    actors: list[FilmPerson] = Field(default_factory=list)
    writers: list[FilmPerson] = Field(default_factory=list)
    directors: list[FilmPerson] = Field(default_factory=list)
