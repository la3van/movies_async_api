"""Пакет с описанием моделей фильма, жанра, персоны и общими моделями."""
from postgres_to_es.models.common import ChangedRecord
from postgres_to_es.models.movies import (
    MovieDocument,
    MovieGenre,
    MoviePerson,
)
from postgres_to_es.models.genre import GenreDocument
from postgres_to_es.models.person import PersonDocument, PersonMovie
from postgres_to_es.models.postgres_models import (
    PostgresFilmGenre,
    PostgresFilmPerson,
    PostgresGenre,
    PostgresFilm,
    PostgresPerson,
    PostgresPersonFilm,
)

__all__ = (
    'ChangedRecord',
    'MovieDocument',
    'MovieGenre',
    'MoviePerson',
    'GenreDocument',
    'PersonDocument',
    'PersonMovie',
    'PostgresFilmGenre',
    'PostgresFilmPerson',
    'PostgresGenre',
    'PostgresFilm',
    'PostgresPerson',
    'PostgresPersonFilm',
)
