"""Схемы API для фильмов."""
from uuid import UUID
from pydantic import BaseModel


class ShortFilmResponse(BaseModel):
    """Краткая модель фильма для списков."""

    uuid: UUID
    title: str
    imdb_rating: float | None


class GenreInFilmResponse(BaseModel):
    """Жанр внутри полной информации о фильме."""

    uuid: UUID
    name: str


class PersonInFilmResponse(BaseModel):
    """Персона внутри полной информации о фильме."""

    uuid: UUID
    full_name: str


class FilmDetailResponse(BaseModel):
    """Полная модель фильма для страницы фильма."""

    uuid: UUID
    title: str
    imdb_rating: float | None
    description: str | None
    genre: list[GenreInFilmResponse]
    actors: list[PersonInFilmResponse]
    writers: list[PersonInFilmResponse]
    directors: list[PersonInFilmResponse]
