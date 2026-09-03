"""Модели данных, получаемых из PostgreSQL."""

from pydantic import BaseModel, ConfigDict, Field


class PostgresFilmGenre(BaseModel):
    """Жанр фильма из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    name: str


class PostgresFilmPerson(BaseModel):
    """Персона фильма из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    full_name: str


class PostgresFilm(BaseModel):
    """Фильм из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    title: str
    description: str | None = None
    imdb_rating: float | None = None
    genre: list[PostgresFilmGenre] = Field(default_factory=list)
    actors: list[PostgresFilmPerson] = Field(default_factory=list)
    writers: list[PostgresFilmPerson] = Field(default_factory=list)
    directors: list[PostgresFilmPerson] = Field(default_factory=list)


class PostgresGenre(BaseModel):
    """Жанр из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    name: str
    description: str | None = None


class PostgresPersonFilm(BaseModel):
    """Фильм, связанный с персоной, из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    roles: list[str] = Field(default_factory=list)


class PostgresPerson(BaseModel):
    """Персона из PostgreSQL."""

    model_config = ConfigDict(extra="forbid")

    uuid: str
    full_name: str
    films: list[PostgresPersonFilm] = Field(default_factory=list)
