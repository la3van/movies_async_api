"""Преобразование моделей персон в схемы API."""

from uuid import UUID

from api.v1.schemas.films import ShortFilmResponse
from api.v1.schemas.persons import (
    PersonFilmResponse,
    PersonResponse,
)
from models.film import ShortFilm
from models.person import Person, PersonFilm


def build_person_film_response(film: PersonFilm) -> PersonFilmResponse:
    """Собирает ответ API для фильма внутри персоны."""
    return PersonFilmResponse(
        uuid=UUID(film.uuid),
        roles=film.roles,
    )


def build_person_response(person: Person) -> PersonResponse:
    """Собирает ответ API для персоны."""
    return PersonResponse(
        uuid=UUID(person.uuid),
        full_name=person.full_name,
        films=[build_person_film_response(film) for film in person.films],
    )


def build_short_film_response(film: ShortFilm) -> ShortFilmResponse:
    """Собирает краткий ответ API для фильма."""
    return ShortFilmResponse(
        uuid=UUID(film.uuid),
        title=film.title,
        imdb_rating=film.imdb_rating,
    )
