"""Преобразование моделей жанров в схемы API."""

from uuid import UUID

from api.v1.schemas.genres import GenreResponse
from models.genre import Genre


def build_genre_response(genre: Genre) -> GenreResponse:
    """Собирает ответ API для жанра."""
    return GenreResponse(
        uuid=UUID(genre.uuid),
        name=genre.name,
    )
