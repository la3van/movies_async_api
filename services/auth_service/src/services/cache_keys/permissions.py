"""Функции создания ключей кеша прав доступа."""

from uuid import UUID


def get_permission_cache_key(permission_id: UUID | str) -> str:
    """Формирует ключ кеша права доступа по идентификатору."""
    return f"permission:{permission_id}"


def get_permissions_cache_key(
    limit: int,
    offset: int,
) -> str:
    """Формирует ключ кеша списка прав доступа."""
    return f"permissions:list:limit={limit}:offset={offset}"


def get_permissions_cache_pattern() -> str:
    """Формирует шаблон ключей кеша списков прав доступа."""
    return "permissions:list:*"
