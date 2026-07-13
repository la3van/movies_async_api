"""Pydantic-схемы истории входов."""
from api.v1.schemas.entity import EntityResponse
from pydantic import Field


class LoginHistoryResponse(EntityResponse):
    """Response-схема записи истории входа."""
    login: str = Field(
        description='Логин, с которым была выполнена попытка входа',
        examples=['ivan'],
    )

    is_successful: bool = Field(
        description='Флаг успешной попытки входа',
        examples=[True],
    )

    reason: str | None = Field(
        description='Причина неуспешной попытки входа',
        examples=['Invalid password'],
    )

    user_agent: str | None = Field(
        description='User-Agent клиента',
        examples=['Mozilla/5.0'],
    )

    ip_address: str | None = Field(
        description='IP-адрес клиента',
        examples=['127.0.0.1'],
    )
