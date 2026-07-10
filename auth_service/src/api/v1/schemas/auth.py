"""Pydantic-схемы аутентификации."""
from pydantic import BaseModel, Field

from api.v1.schemas.users import UserCreate, UserResponse


class RegisterRequest(UserCreate):
    """Request-схема регистрации пользователя."""


class LoginRequest(BaseModel):
    """Request-схема логина пользователя."""
    login: str = Field(
        min_length=1,
        max_length=255,
        description='Логин пользователя',
        examples=['ivan'],
    )

    password: str = Field(
        min_length=1,
        max_length=128,
        description='Пароль пользователя',
        examples=['strong_password'],
    )


class TokenPairResponse(BaseModel):
    """Response-схема пары токенов."""
    access_token: str = Field(
        description='JWT access-token',
        examples=['eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'],
    )

    refresh_token: str = Field(
        description='Refresh-token для обновления пары токенов',
        examples=['z6Y9q7N7Zp4M...'],
    )

    token_type: str = Field(
        default='bearer',
        description='Тип токена для Authorization header',
        examples=['bearer'],
    )


class RefreshTokenRequest(BaseModel):
    """Request-схема обновления токенов."""
    refresh_token: str = Field(
        description='Refresh-token пользователя',
        examples=['z6Y9q7N7Zp4M...'],
    )


class LogoutRequest(BaseModel):
    """Request-схема logout."""
    refresh_token: str = Field(
        description='Refresh-token сессии, которую нужно завершить',
        examples=['z6Y9q7N7Zp4M...'],
    )


class AuthUserResponse(BaseModel):
    """Response-схема текущего пользователя."""
    user: UserResponse = Field(
        description='Текущий аутентифицированный пользователь',
    )
