"""Pydantic-схемы permissions."""
from pydantic import BaseModel, Field

from api.v1.schemas.entity import EntityResponse


class PermissionBase(BaseModel):
    """Базовая схема permission."""
    code: str = Field(
        min_length=1,
        max_length=100,
        description='Код права доступа',
        examples=['movies:watch_premium'],
    )

    description: str | None = Field(
        default=None,
        description='Описание права доступа',
        examples=['Разрешает смотреть премиум-фильмы'],
    )


class PermissionCreate(PermissionBase):
    """Схема создания permission."""


class PermissionUpdate(BaseModel):
    """Схема обновления permission."""
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description='Новый код права доступа',
        examples=['movies:watch_fresh'],
    )

    description: str | None = Field(
        default=None,
        description='Новое описание права доступа',
        examples=['Разрешает смотреть новые фильмы'],
    )


class PermissionResponse(PermissionBase, EntityResponse):
    """Response-схема permission."""


class PermissionCheckRequest(BaseModel):
    """Request-схема проверки права доступа."""
    permission_code: str = Field(
        min_length=1,
        max_length=100,
        description='Код права доступа, которое нужно проверить',
        examples=['movies:watch_fresh'],
    )


class PermissionCheckResponse(BaseModel):
    """Response-схема проверки права доступа."""
    has_permission: bool = Field(
        description='Есть ли у пользователя указанное право доступа',
        examples=[True],
    )
