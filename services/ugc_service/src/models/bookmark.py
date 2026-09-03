"""Доменная модель пользовательской закладки."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Bookmark(BaseModel):
    """Связь пользователя с отложенным фильмом."""

    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    film_id: UUID
    created_at: datetime
