"""API-схемы оценок фильмов."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StrictInt


class RatingUpsertRequest(BaseModel):
    """Создание или изменение пользовательской оценки."""

    value: Annotated[StrictInt, Field(ge=0, le=10)]


class RatingResponse(BaseModel):
    """Оценка текущего пользователя."""

    film_id: UUID
    value: int = Field(ge=0, le=10)
    created_at: datetime
    updated_at: datetime


class RatingDistributionResponse(BaseModel):
    """Количество оценок с конкретным значением."""

    value: int = Field(ge=0, le=10)
    count: int = Field(ge=0)


class FilmRatingStatsResponse(BaseModel):
    """Сводная пользовательская оценка фильма."""

    film_id: UUID
    rating_count: int = Field(ge=0)
    average_rating: float | None
    likes_count: int = Field(ge=0)
    dislikes_count: int = Field(ge=0)
    distribution: list[RatingDistributionResponse]
