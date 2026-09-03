"""Тестовые данные для users эндпоинтов."""

from tests.functional.test_data.common import UNSET, UnsetType

UPDATED_FIRST_NAME = "Updated"
UPDATED_LAST_NAME = "User"

NEW_PASSWORD = "new_password123"
WRONG_OLD_PASSWORD = "wrong_old_password123"


def get_update_profile_data(
    *,
    first_name: str | None | UnsetType = UNSET,
    last_name: str | None | UnsetType = UNSET,
) -> dict[str, str | None]:
    """Возвращает payload частичного обновления профиля пользователя."""
    data: dict[str, str | None] = {}

    if not isinstance(first_name, UnsetType):
        data["first_name"] = first_name

    if not isinstance(last_name, UnsetType):
        data["last_name"] = last_name

    return data


def get_full_update_profile_data() -> dict[str, str | None]:
    """Возвращает payload обновления имени и фамилии пользователя."""
    return get_update_profile_data(
        first_name=UPDATED_FIRST_NAME,
        last_name=UPDATED_LAST_NAME,
    )


def get_change_password_data(
    *,
    old_password: str,
    new_password: str = NEW_PASSWORD,
) -> dict[str, str]:
    """Возвращает payload смены пароля."""
    return {
        "old_password": old_password,
        "new_password": new_password,
    }


def get_wrong_old_password_data() -> dict[str, str]:
    """Возвращает payload смены пароля с неверным старым паролем."""
    return {
        "old_password": WRONG_OLD_PASSWORD,
        "new_password": NEW_PASSWORD,
    }
