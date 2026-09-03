"""Доменные модели оценки фильма."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Rating(BaseModel):
    """Оценка фильма пользователем от 0 до 10."""

    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    film_id: UUID
    value: int = Field(ge=0, le=10)
    created_at: datetime
    updated_at: datetime


class RatingDistributionItem(BaseModel):
    """Количество оценок с определённым значением."""

    value: int = Field(ge=0, le=10)
    count: int = Field(ge=0)


class FilmRatingStats(BaseModel):
    """Агрегированная пользовательская оценка фильма."""

    film_id: UUID
    rating_count: int = Field(ge=0)
    average_rating: float | None
    likes_count: int = Field(ge=0)
    dislikes_count: int = Field(ge=0)
    distribution: list[RatingDistributionItem]
