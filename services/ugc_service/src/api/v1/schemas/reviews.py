"""API-схемы рецензий и голосов."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewCreateRequest(BaseModel):
    """Текст новой рецензии."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=10_000)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("review text must not be blank")
        return value


class ReviewUpdateRequest(ReviewCreateRequest):
    """Новый текст существующей рецензии."""


class ReviewResponse(BaseModel):
    """Рецензия с рейтингом автора и пользовательскими голосами."""

    id: UUID
    film_id: UUID
    author_id: UUID
    author_login: str
    text: str
    published_at: datetime
    updated_at: datetime
    likes_count: int = Field(ge=0)
    dislikes_count: int = Field(ge=0)
    helpfulness: int
    author_rating: int | None = Field(default=None, ge=0, le=10)


class ReviewPageResponse(BaseModel):
    """Страница рецензий с курсором продолжения."""

    items: list[ReviewResponse]
    next_cursor: str | None = None


class ReactionUpsertRequest(BaseModel):
    """Лайк или дизлайк рецензии."""

    model_config = ConfigDict(extra="forbid")
    value: Literal["like", "dislike"]


class ReactionResponse(BaseModel):
    """Голос текущего пользователя за рецензию."""

    review_id: UUID
    value: Literal["like", "dislike"]
    created_at: datetime
    updated_at: datetime
