"""Pydantic-схемы пользователей."""
from pydantic import BaseModel, EmailStr, Field

from api.v1.schemas.entity import EntityResponse
from api.v1.schemas.roles import RoleResponse


class UserBase(BaseModel):
    """Базовая схема пользователя."""
    login: str = Field(
        min_length=1,
        max_length=100,
        description='Логин пользователя.',
        examples=['ivan'],
    )

    email: EmailStr = Field(
        description='Email пользователя',
        examples=['ivan@example.com'],
    )

    first_name: str | None = Field(
        default=None,
        max_length=255,
        description='Имя пользователя',
        exmaples=['Ivan'],
    )

    last_name: str | None = Field(
        default=None,
        max_length=255,
        description='Фамилия пользователя',
        examples=['Ivanov'],
    )


class UserCreate(UserBase):
    """Схема создания пользователя."""
    password: str = Field(
        min_length=8,
        max_length=128,
        description='Пароль пользователя',
        examples=['strong_password']
    )


class UserUpdate(BaseModel):
    """Схема обновления профиля пользователя."""
    first_name: str | None = Field(
        default=None,
        max_length=255,
        description='Новое имя пользователя',
        examples=['Ivan'],
    )

    last_name: str | None = Field(
        default=None,
        max_length=255,
        description='Новая фамилия пользователя',
        examples=['Ivanov'],
    )


class UserPasswordUpdate(BaseModel):
    """Схема смены пароля пользователя."""
    old_password: str = Field(
        min_length=8,
        max_length=128,
        description='Текущий пароль пользователя',
        examples=['old_password'],
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
        description='Новый пароль пользователя',
        examples=['new_strong_password'],
    )


class UserResponse(UserBase, EntityResponse):
    """Response-схема пользователя."""
    is_active: bool = Field(
        description='Флаг активного пользователя',
        examples=[True],
    )

    is_superuser: bool = Field(
        description='Флаг суперпользователя',
        examples=[False],
    )

    roles: list[RoleResponse] = Field(
        default_factory=list,
        description='Список ролей пользователя',
    )
