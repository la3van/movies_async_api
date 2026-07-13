"""Функции построения ожидаемых API-ответов."""
from typing import Any


def genre_to_response(document: dict[str, Any]) -> dict[str, Any]:
    """Преобразует документ жанра в ожидаемый API-ответ."""
    return {
        'uuid': document['uuid'],
        'name': document['name'],
    }


def movie_to_short_response(document: dict[str, Any]) -> dict[str, Any]:
    """Преобразует документ фильма в краткий API-ответ."""
    return {
        'uuid': document['uuid'],
        'title': document['title'],
        'imdb_rating': document['imdb_rating'],
    }
