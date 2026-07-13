"""Преобразование моделей жанров в схемы API."""
from uuid import UUID

from models.genre import Genre

from api.v1.schemas.genres import GenreResponse


def build_genre_response(genre: Genre) -> GenreResponse:
    """Собирает ответ API для жанра."""
    return GenreResponse(
        uuid=UUID(genre.uuid),
        name=genre.name,
    )
