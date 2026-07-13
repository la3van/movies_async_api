"""Тестовые данные для roles эндпоинтов."""
from uuid import UUID

from .permissions import MISSING_PERMISSION_ID

ROLE_NAME = 'subscriber'
ROLE_DESCRIPTION = 'Пользователь с активной подпиской'
ROLE_IS_DEFAULT = False

SECOND_ROLE_NAME = 'admin'
SECOND_ROLE_DESCRIPTION = 'Администратор auth-сервиса'

UPDATED_ROLE_NAME = 'premium_subscriber'
UPDATED_ROLE_DESCRIPTION = 'Пользователь с премиум-подпиской'

MISSING_ROLE_ID = '00000000-0000-0000-0000-000000000002'


def get_role_create_data(
    *,
    name: str = ROLE_NAME,
    description: str | None = ROLE_DESCRIPTION,
    is_default: bool = ROLE_IS_DEFAULT,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str]]:
    """Возвращает payload создания роли."""
    return {
        'name': name,
        'descriptio': description,
        'is_default': is_default,
        'permission_ids': [
            str(permission_id) for permission_id in permission_ids or []
        ],
    }


def get_second_role_create_data(
    *,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str]]:
    """Возвращает payload создания второй роли."""
    return get_role_create_data(
        name=SECOND_ROLE_NAME,
        description=SECOND_ROLE_DESCRIPTION,
        permission_ids=permission_ids,
    )


def get_role_update_data(
    *,
    name: str | None = UPDATED_ROLE_NAME,
    description: str | None = UPDATED_ROLE_DESCRIPTION,
    is_default: bool | None = None,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str] | None]:
    """Возвращает payload обновления роли."""
    data: dict[str, str | bool | list[str] | None] = {
        'name': name,
        'description': description,
        'is_default': is_default,
    }

    if permission_ids is not None:
        data['permission_ids'] = [
            str(permission_id) for permission_id in permission_ids
        ]

    return data


def get_duplicate_role_create_data() -> dict[str, str | bool | list[str]]:
    """Возвращает payload создания роли с уже существующим name."""
    return get_role_create_data(name=ROLE_NAME)


def get_role_with_missing_permission_data(
) -> dict[str, str | bool | list[str]]:
    """Возвращает payload создания роли с несуществующим permission_id."""
    return get_role_create_data(permission_ids=[MISSING_PERMISSION_ID])
