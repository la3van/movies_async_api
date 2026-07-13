"""Функции создания ключей кеша пользователей."""
from uuid import UUID


def get_user_cache_key(user_id: UUID | str) -> str:
    """Формирует ключ кеша профиля пользователя."""
    return f'user:profile:{user_id}'


def get_users_cache_pattern() -> str:
    """Формирует шаблон ключей кеша для профилей пользователя."""
    return 'user:profile:*'


def get_login_history_cache_key(
    user_id: UUID | str,
    limit: int,
    offset: int,
) -> str:
    """Формирует ключ кеша истории входа пользователя."""
    return f'user:{user_id}:login_history:limit={limit}:offset={offset}'


def get_login_history_cache_pattern(
    user_id: UUID | str,
) -> str:
    """Формирует шаблон ключей истории входов пользователя."""
    return f'user:{user_id}:login_history:*'
