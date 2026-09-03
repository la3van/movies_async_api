"""Функции создания ключей кеша пользователей."""

from datetime import datetime
from uuid import UUID


def get_user_cache_key(user_id: UUID | str) -> str:
    """Формирует ключ кеша профиля пользователя."""
    return f"user:profile:{user_id}"


def get_users_cache_pattern() -> str:
    """Формирует шаблон ключей кеша для профилей пользователя."""
    return "user:profile:*"


def get_login_history_cache_key(
    user_id: UUID | str,
    limit: int,
    offset: int,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> str:
    """Формирует ключ кеша истории входа пользователя."""
    created_from_value = (
        created_from.isoformat() if created_from is not None else "none"
    )
    created_to_value = (
        created_to.isoformat() if created_to is not None else "none"
    )

    return (
        f"user:{user_id}:login_history:"
        f"limit={limit}:offset={offset}:"
        f"from={created_from_value}:"
        f"to={created_to_value}"
    )


def get_login_history_cache_pattern(
    user_id: UUID | str,
) -> str:
    """Формирует шаблон ключей истории входов пользователя."""
    return f"user:{user_id}:login_history:*"
