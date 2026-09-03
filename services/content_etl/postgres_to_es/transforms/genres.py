"""Трансформация жанров из PostgreSQL в документы индекса genres."""

from postgres_to_es.models import GenreDocument, PostgresGenre


def transform_genre(genre: PostgresGenre) -> GenreDocument:
    """Преобразует жанр из PostgreSQL в документ индекса genres."""
    return GenreDocument(
        uuid=genre.uuid,
        name=genre.name,
        description=genre.description,
    )


def transform_genres(genres: list[PostgresGenre]) -> list[GenreDocument]:
    """Преобразует список жанров из PostgreSQL в документы индекса genres."""
    result: list[GenreDocument] = []
    seen: set[str] = set()

    for genre in genres:
        if genre.uuid in seen:
            continue

        result.append(transform_genre(genre))
        seen.add(genre.uuid)

    return result
