"""Модели интеграции с Auth Service."""
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
    StrictStr,
    Field(min_length=1),
]


class AccessTokenClaims(BaseModel):
    """Проверенные данные access token."""
    model_config = ConfigDict(extra='ignore')

    sub: UUID
    type: Literal['access']

    iat: StrictInt
    exp: StrictInt

    login: NonEmptyStrictString
    roles: list[StrictStr]
    permissions: list[StrictStr]
    is_superuser: StrictBool


class PermissionDecision(BaseModel):
    """Решение о наличии permission."""
    has_permission: StrictBool
