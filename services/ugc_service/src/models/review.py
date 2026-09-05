"""Доменные модели рецензий."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Review(BaseModel):
    """Пользовательская рецензия на фильм."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    film_id: UUID
    user_id: UUID
    author_login: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=10_000)
    created_at: datetime
    updated_at: datetime


class ReviewDetails(Review):
    """Рецензия с данными из связанных коллекций."""

    likes_count: int = Field(ge=0)
    dislikes_count: int = Field(ge=0)
    helpfulness: int
    author_rating: int | None = Field(default=None, ge=0, le=10)


class ReviewPage(BaseModel):
    """Страница рецензий и курсор следующей страницы."""

    items: list[ReviewDetails]
    next_cursor: str | None = None
