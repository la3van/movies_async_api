"""Тестовые данные для roles эндпоинтов."""

from uuid import UUID

from tests.functional.test_data.common import UNSET, UnsetType

from .permissions import MISSING_PERMISSION_ID

ROLE_NAME = "subscriber"
ROLE_DESCRIPTION = "Пользователь с активной подпиской"
ROLE_IS_DEFAULT = False

SECOND_ROLE_NAME = "admin"
SECOND_ROLE_DESCRIPTION = "Администратор auth-сервиса"

UPDATED_ROLE_NAME = "premium_subscriber"
UPDATED_ROLE_DESCRIPTION = "Пользователь с премиум-подпиской"

MISSING_ROLE_ID = "00000000-0000-0000-0000-000000000002"


def get_role_create_data(
    *,
    name: str = ROLE_NAME,
    description: str | None = ROLE_DESCRIPTION,
    is_default: bool = ROLE_IS_DEFAULT,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str] | None]:
    """Возвращает payload создания роли."""
    return {
        "name": name,
        "description": description,
        "is_default": is_default,
        "permission_ids": [
            str(permission_id) for permission_id in permission_ids or []
        ],
    }


def get_second_role_create_data(
    *,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str] | None]:
    """Возвращает payload создания второй роли."""
    return get_role_create_data(
        name=SECOND_ROLE_NAME,
        description=SECOND_ROLE_DESCRIPTION,
        permission_ids=permission_ids,
    )


def get_role_update_data(
    *,
    name: str | None | UnsetType = UNSET,
    description: str | None | UnsetType = UNSET,
    is_default: bool | None | UnsetType = UNSET,
    permission_ids: list[UUID | str] | None | UnsetType = UNSET,
) -> dict[str, str | bool | list[str] | None]:
    """Возвращает payload частичного обновления роли."""
    data: dict[str, str | bool | list[str] | None] = {}

    if not isinstance(name, UnsetType):
        data["name"] = name
    if not isinstance(description, UnsetType):
        data["description"] = description
    if not isinstance(is_default, UnsetType):
        data["is_default"] = is_default
    if not isinstance(permission_ids, UnsetType):
        data["permission_ids"] = (
            None
            if permission_ids is None
            else [str(permission_id) for permission_id in permission_ids]
        )

    return data


def get_full_role_update_data(
    *,
    permission_ids: list[UUID | str] | None = None,
) -> dict[str, str | bool | list[str] | None]:
    """Возвращает payload обновления всех основных полей роли."""
    return get_role_update_data(
        name=UPDATED_ROLE_NAME,
        description=UPDATED_ROLE_DESCRIPTION,
        is_default=True,
        permission_ids=permission_ids or [],
    )


def get_duplicate_role_create_data() -> dict[
    str, str | bool | list[str] | None
]:
    """Возвращает payload создания роли с уже существующим name."""
    return get_role_create_data(name=ROLE_NAME)


def get_role_with_missing_permission_data() -> dict[
    str, str | bool | list[str] | None
]:
    """Возвращает payload создания роли с несуществующим permission_id."""
    return get_role_create_data(permission_ids=[MISSING_PERMISSION_ID])
