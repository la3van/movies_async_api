"""Pydantic-схемы permissions."""
from pydantic import BaseModel, Field

from api.v1.schemas.entity import EntityResponse


class PermissionBase(BaseModel):
    """Базовая схема permission."""
    code: str = Field(
        min_length=1,
        max_length=100,
        description='Код права доступа',
        exmaples=['movies:watch_premium'],
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
        exmaples=['movies:watch_fresh'],
    )

    description: str | None = Field(
        default=None,
        description='Новое описание права доступа',
        exmaples=['Разрешает смотреть новые фильмы'],
    )


class PermissionResponse(PermissionBase, EntityResponse):
    """Response-схема permission."""
