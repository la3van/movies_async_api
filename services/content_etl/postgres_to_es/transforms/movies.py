"""Трансформация фильмов из PostgreSQL в документы индекса movies."""
from postgres_to_es.models import (
    MovieDocument,
    MovieGenre,
    MoviePerson,
    PostgresFilm,
    PostgresFilmGenre,
    PostgresFilmPerson,
)


def _unique_genres(genres: list[PostgresFilmGenre]) -> list[MovieGenre]:
    """Возвращает уникальные жанры с сохранением исходного порядка."""
    result: list[MovieGenre] = []
    seen: set[str] = set()

    for genre in genres:
        if genre.uuid in seen:
            continue

        result.append(
            MovieGenre(
                uuid=genre.uuid,
                name=genre.name,
            ),
        )
        seen.add(genre.uuid)

    return result


def _unique_persons(persons: list[PostgresFilmPerson]) -> list[MoviePerson]:
    """Возвращает уникальные персоны с сохранением исходного порядка."""
    result: list[MoviePerson] = []
    seen: set[str] = set()

    for person in persons:
        if person.uuid in seen:
            continue

        result.append(
            MoviePerson(
                uuid=person.uuid,
                full_name=person.full_name,
            ),
        )
        seen.add(person.uuid)

    return result


def transform_film(film: PostgresFilm) -> MovieDocument:
    """Преобразует фильм из PostgreSQL в документ индекса movies."""
    return MovieDocument(
        uuid=film.uuid,
        imdb_rating=film.imdb_rating,
        title=film.title,
        description=film.description,
        genre=_unique_genres(film.genre),
        actors=_unique_persons(film.actors),
        writers=_unique_persons(film.writers),
        directors=_unique_persons(film.directors),
    )


def transform_films(films: list[PostgresFilm]) -> list[MovieDocument]:
    """Преобразует список фильмов из PostgreSQL в документы индекса movies."""
    return [transform_film(film) for film in films]
