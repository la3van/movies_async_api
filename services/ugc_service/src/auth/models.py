"""Модели аутентификации."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

NonEmptyStrictString = Annotated[
    StrictStr, Field(min_length=1, max_length=100)
]


class AuthServiceUser(BaseModel):
    """Минимальная часть ответа GET /users/me."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    login: NonEmptyStrictString
    is_active: StrictBool


class AuthenticatedUser(BaseModel):
    """Проверенная идентичность для бизнес-операций."""

    id: UUID
    login: str
    access_token: str = Field(repr=False)
