"""Pydantic-схемы ролей."""
from uuid import UUID

from pydantic import BaseModel, Field

from api.v1.schemas.entity import EntityResponse
from api.v1.schemas.permissions import PermissionResponse


class RoleBase(BaseModel):
    """Базовая схема роли."""
    name: str = Field(
        min_length=1,
        max_length=100,
        description='Название роли',
        exmaples=['subscriber'],
    )

    description: str | None = Field(
        default=None,
        description='Описание роли',
        exmaples=['Пользователь с активной подпиской'],
    )

    is_default: bool = Field(
        default=False,
        description='Флаг роли, которая выдаётся пользователю по умолчанию',
        examples=[False],
    )


class RoleCreate(RoleBase):
    """Схема создания роли."""
    permission_ids: list[UUID] = Field(
        default_factory=list,
        description=(
            'Список идентификаторов permissions,'
            'которые нужно привязать к роли'
        ),
        examples=[['6f822a92-7b51-4753-8d00-ecfedf98a937']],
    )


class RoleUpdate(BaseModel):
    """Схема обновления роли."""
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description='Новое название роли',
        examples=['admin'],
    )

    description: str | None = Field(
        default=None,
        description='Новое описание роли',
        examples=['Администратор auth-сервиса'],
    )

    is_default: bool | None = Field(
        default=None,
        description='Новый флаг роли по умолчанию',
        examples=[False],
    )

    permission_ids: list[UUID] | None = Field(
        default=None,
        description='Новый список permissions роли',
        exmaples=[['6f822a92-7b51-4753-8d00-ecfedf98a937']],
    )


class RoleResponse(RoleBase, EntityResponse):
    """Response-схема роли."""
    permissions: list[PermissionResponse] = Field(
        default_factory=list,
        description='Список прав доступа, привязанных к роли',
    )
