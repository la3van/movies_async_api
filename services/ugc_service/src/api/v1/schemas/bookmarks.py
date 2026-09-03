"""API-схемы закладок."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BookmarkResponse(BaseModel):
    """Добавленный пользователем фильм."""

    film_id: UUID = Field(description="UUID фильма")
    created_at: datetime = Field(description="Дата добавления в закладки")
