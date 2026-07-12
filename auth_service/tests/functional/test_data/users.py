"""Тестовые данные для users эндпоинтов."""
UPDATED_FIRST_NAME = 'Updated'
UPDATED_LAST_NAME = 'User'

NEW_PASSWORD = 'new_password123'
WRONG_OLD_PASSWORD = 'wrong_old_password123'


def get_update_profile_data(
    *,
    first_name: str | None = UPDATED_FIRST_NAME,
    last_name: str | None = UPDATED_LAST_NAME,
) -> dict[str, str | None]:
    """Возвращает payload обновления профиля пользователя."""
    return {
        'first_name': first_name,
        'last_name': last_name,
    }


def get_change_password_data(
    *,
    old_password: str,
    new_password: str = NEW_PASSWORD,
) -> dict[str, str]:
    """Возвращает payload смены пароля."""
    return {
        'old_password': old_password,
        'new_password': new_password,
    }


def get_wrong_old_password_data() -> dict[str, str]:
    """Возвращает payload смены пароля с неверным старым паролем."""
    return {
        'old_password': WRONG_OLD_PASSWORD,
        'new_password': NEW_PASSWORD,
    }
