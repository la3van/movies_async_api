"""Функции создания ключей кеша ролей."""

from uuid import UUID


def get_role_cache_key(role_id: UUID | str) -> str:
    """Формирует ключ кеша роли по идентификатору."""
    return f"role:{role_id}"


def get_role_cache_pattern() -> str:
    """Формирует шаблон ключей отдельных ролей."""
    return "role:*"


def get_roles_cache_key(
    limit: int,
    offset: int,
) -> str:
    """Формирует ключ кеша списка ролей."""
    return f"roles:list:limit={limit}:offset={offset}"


def get_roles_cache_pattern() -> str:
    """Формирует шаблон ключей кеша списков ролей."""
    return "roles:list:*"
