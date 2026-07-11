"""Функции создания ключей кеша ролей."""
from uuid import UUID


def get_role_cache_key(role_id: UUID | str) -> str:
    """Формирует ключ кеша роли по идентификатору."""
    return f'role:{role_id}'


def get_default_roles_cache_key() -> str:
    """Формирует ключ кеша ролей по умолчанию."""
    return 'roles:default'
