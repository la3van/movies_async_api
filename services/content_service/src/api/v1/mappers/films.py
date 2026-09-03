"""Преобразование моделей фильмов в схемы API."""

from uuid import UUID

from api.v1.schemas.films import (
    FilmDetailResponse,
    GenreInFilmResponse,
    PersonInFilmResponse,
    ShortFilmResponse,
)
from models.film import Film, ShortFilm


def build_short_film_response(film: ShortFilm) -> ShortFilmResponse:
    """Собирает краткий ответ API для фильма."""
    return ShortFilmResponse(
        uuid=UUID(film.uuid),
        title=film.title,
        imdb_rating=film.imdb_rating,
    )


def build_film_detail_response(film: Film) -> FilmDetailResponse:
    """Собирает полный ответ API для фильма."""
    return FilmDetailResponse(
        uuid=UUID(film.uuid),
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genre=[
            GenreInFilmResponse(
                uuid=UUID(genre.uuid),
                name=genre.name,
            )
            for genre in film.genre
        ],
        actors=[
            PersonInFilmResponse(
                uuid=UUID(actor.uuid),
                full_name=actor.full_name,
            )
            for actor in film.actors
        ],
        writers=[
            PersonInFilmResponse(
                uuid=UUID(writer.uuid),
                full_name=writer.full_name,
            )
            for writer in film.writers
        ],
        directors=[
            PersonInFilmResponse(
                uuid=UUID(director.uuid),
                full_name=director.full_name,
            )
            for director in film.directors
        ],
    )
