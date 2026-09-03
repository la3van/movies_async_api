"""Пакет с описанием моделей фильма, жанра, персоны и общими моделями."""

from postgres_to_es.models.common import BaseDocument, ChangedRecord
from postgres_to_es.models.genre import GenreDocument
from postgres_to_es.models.movies import (
    MovieDocument,
    MovieGenre,
    MoviePerson,
)
from postgres_to_es.models.person import PersonDocument, PersonMovie
from postgres_to_es.models.postgres_models import (
    PostgresFilm,
    PostgresFilmGenre,
    PostgresFilmPerson,
    PostgresGenre,
    PostgresPerson,
    PostgresPersonFilm,
)

__all__ = (
    "BaseDocument",
    "ChangedRecord",
    "GenreDocument",
    "MovieDocument",
    "MovieGenre",
    "MoviePerson",
    "PersonDocument",
    "PersonMovie",
    "PostgresFilm",
    "PostgresFilmGenre",
    "PostgresFilmPerson",
    "PostgresGenre",
    "PostgresPerson",
    "PostgresPersonFilm",
)
