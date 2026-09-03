"""Модели интеграции Events Service с Auth Service."""

from uuid import UUID

from pydantic import BaseModel


class AuthenticatedUser(BaseModel):
    """Минимальные данные проверенного пользователя Auth Service."""

    id: UUID
