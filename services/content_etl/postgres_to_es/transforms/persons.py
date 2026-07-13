"""Трансформация персон из PostgreSQL в документы индекса persons."""
from postgres_to_es.models import (
    PersonDocument,
    PersonMovie,
    PostgresPerson,
    PostgresPersonFilm,
)


def _unique_roles(roles: list[str]) -> list[str]:
    """Возвращает уникальные роли с сохранением исходного порядка."""
    result: list[str] = []
    seen: set[str] = set()

    for role in roles:
        if role in seen:
            continue

        result.append(role)
        seen.add(role)

    return result


def _unique_person_films(
    films: list[PostgresPersonFilm],
) -> list[PersonMovie]:
    """Возвращает уникальные фильмы персоны с объединением ролей."""
    films_by_uuid: dict[str, PersonMovie] = {}

    for film in films:
        if film.uuid not in films_by_uuid:
            films_by_uuid[film.uuid] = PersonMovie(
                uuid=film.uuid,
                roles=[],
            )

        current_roles = films_by_uuid[film.uuid].roles
        films_by_uuid[film.uuid].roles = _unique_roles(
            current_roles + film.roles,
        )

    return list(films_by_uuid.values())


def transform_person(person: PostgresPerson) -> PersonDocument:
    """Преобразует персону из PostgreSQL в документ индекса persons."""
    return PersonDocument(
        uuid=person.uuid,
        full_name=person.full_name,
        films=_unique_person_films(person.films),
    )


def transform_persons(
    persons: list[PostgresPerson],
) -> list[PersonDocument]:
    """Преобразует список персон из PostgreSQL в документы индекса persons."""
    result: list[PersonDocument] = []
    seen: set[str] = set()

    for person in persons:
        if person.uuid in seen:
            continue

        result.append(transform_person(person))
        seen.add(person.uuid)

    return result
