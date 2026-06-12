"""Модели документов фильмов для Elasticsearch."""
from pydantic import BaseModel, ConfigDict, Field


class MovieGenre(BaseModel):
    """Жанр внутри документа фильма."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    name: str


class MoviePerson(BaseModel):
    """Персона внутри документа фильма."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    full_name: str


class MovieDocument(BaseModel):
    """Документ фильма для индекса Elasticsearch."""
    model_config = ConfigDict(extra='forbid')

    uuid: str
    imdb_rating: float | None = None
    title: str
    description: str | None = None

    genre: list[MovieGenre] = Field(default_factory=list)
    actors: list[MoviePerson] = Field(default_factory=list)
    writers: list[MoviePerson] = Field(default_factory=list)
    directors: list[MoviePerson] = Field(default_factory=list)
