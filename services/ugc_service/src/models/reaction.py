"""Доменные модели голосования за рецензии."""

from datetime import datetime
from enum import IntEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReactionValue(IntEnum):
    """Направление пользовательского голоса."""

    DISLIKE = -1
    LIKE = 1


class ReviewReaction(BaseModel):
    """Лайк или дизлайк рецензии конкретным пользователем."""

    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    review_id: UUID
    value: ReactionValue
    created_at: datetime
    updated_at: datetime
