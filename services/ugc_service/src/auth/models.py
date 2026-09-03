"""Модели аутентификации."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
)

NonEmptyStrictString = Annotated[
    StrictStr, Field(min_length=1, max_length=100)
]


class AccessTokenClaims(BaseModel):
    """Проверенные claims access JWT."""

    model_config = ConfigDict(extra="ignore")
    sub: UUID
    type: Literal["access"]
    iat: StrictInt
    exp: StrictInt
    login: NonEmptyStrictString
    is_superuser: StrictBool = False


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
