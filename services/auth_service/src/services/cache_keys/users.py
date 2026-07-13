"""Функции создания ключей кеша пользователей."""
from uuid import UUID


def get_user_cache_key(user_id: UUID | str) -> str:
    """Формирует ключ кеша пользователя по идентификатору."""
    return f'user:{user_id}'


def get_login_history_cache_key(
    user_id: UUID | str,
    limit: int,
    offset: int,
) -> str:
    """Формирует ключ кеша истории входа пользователя."""
    return f'user:{user_id}:login_history:limit={limit}:offset={offset}'
