"""Преобразование документов Elasticsearch в модели фильмов."""

from typing import Any

from models.film import ShortFilm


def build_short_film(source: dict[str, Any]) -> ShortFilm:
    """Собирает краткую модель фильма из документа Elasticsearch."""
    return ShortFilm(
        uuid=source["uuid"],
        title=source["title"],
        imdb_rating=source.get("imdb_rating"),
    )
