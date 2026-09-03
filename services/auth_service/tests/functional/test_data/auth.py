"""Тестовые данные для auth эндпоинтов."""

VALID_USER_LOGIN = "test_user"
VALID_USER_EMAIL = "test_user@example.com"
VALID_USER_PASSWORD = "password123"
VALID_USER_FIRST_NAME = "Test"
VALID_USER_LAST_NAME = "User"

SECOND_USER_LOGIN = "second_user"
SECOND_USER_EMAIL = "second_user@example.com"
SECOND_USER_PASSWORD = "second_password123"

MISSING_USER_LOGIN = "missing_user"
WRONG_PASSWORD = "wrong_password123"

INVALID_EMAIL = "not-an-email"
SHORT_PASSWORD = "short"

INVALID_REFRESH_TOKEN = "invalid-refresh-token"


def get_register_data(
    *,
    login: str = VALID_USER_LOGIN,
    email: str = VALID_USER_EMAIL,
    password: str = VALID_USER_PASSWORD,
    first_name: str | None = VALID_USER_FIRST_NAME,
    last_name: str | None = VALID_USER_LAST_NAME,
) -> dict[str, str | None]:
    """Возвращает payload регистрации пользователя."""
    return {
        "login": login,
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
    }


def get_second_register_data() -> dict[str, str | None]:
    """Возвращает payload регистрации второго пользователя."""
    return get_register_data(
        login=SECOND_USER_LOGIN,
        email=SECOND_USER_EMAIL,
        password=SECOND_USER_PASSWORD,
    )


def get_duplicate_login_register_data() -> dict[str, str | None]:
    """Возвращает payload регистрации с уже сущетсвующим login."""
    return get_register_data(
        login=VALID_USER_LOGIN,
        email="another_email@example.com",
    )


def get_duplicate_email_register_data() -> dict[str, str | None]:
    """Возвращает payload регистрации с уже сущетсвующим email."""
    return get_register_data(
        login="another_login",
        email=VALID_USER_EMAIL,
    )


def get_invalid_email_register_data() -> dict[str, str | None]:
    """Возвращает payload регистрации с невалидным email."""
    return get_register_data(email=INVALID_EMAIL)


def get_short_password_register_data() -> dict[str, str | None]:
    """Возвращает payload регистрации со слишком коротким паролем."""
    return get_register_data(password=SHORT_PASSWORD)


def get_login_data(
    *,
    login: str = VALID_USER_LOGIN,
    password: str = VALID_USER_PASSWORD,
) -> dict[str, str]:
    """Возвращает payload логина пользователя."""
    return {
        "login": login,
        "password": password,
    }


def get_wrong_password_login_data() -> dict[str, str]:
    """Возвращает payload логина с неверным паролем."""
    return get_login_data(password=WRONG_PASSWORD)


def get_missing_user_login_data() -> dict[str, str]:
    """Возвращает payload логина несуществующего пользователя."""
    return get_login_data(
        login=MISSING_USER_LOGIN,
    )


def get_refresh_data(refresh_token: str) -> dict[str, str]:
    """Возвращает payload обновления токенов."""
    return {
        "refresh_token": refresh_token,
    }


def get_logout_data(refresh_token: str) -> dict[str, str]:
    """Возвращает payload logout."""
    return {
        "refresh_token": refresh_token,
    }


def get_invalid_refresh_data() -> dict[str, str]:
    """Возвращает payload с невалидным refresh-токеном."""
    return {
        "refresh_token": INVALID_REFRESH_TOKEN,
    }
