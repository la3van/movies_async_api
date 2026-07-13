"""Функции создания ключей кеша прав доступа."""
from uuid import UUID


def get_permission_cache_key(permission_id: UUID | str) -> str:
    """Формирует ключ кеша права доступа по идентификатору."""
    return f'permission:{permission_id}'
