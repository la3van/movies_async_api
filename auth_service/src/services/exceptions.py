"""Исключения сервисного слоя auth-сервиса."""


class AuthServiceError(Exception):
    """Базовое исключение auth-сервиса."""


class UserAlreadyExistsError(AuthServiceError):
    """Ошибка существующего пользователя."""


class UserNotFoundError(AuthServiceError):
    """Ошибка отсутствующего пользователя."""


class InvalidCredentialsError(AuthServiceError):
    """Ошибка неверных учётных данных."""


class InactiveUserError(AuthServiceError):
    """Ошибка неактивного пользователя."""


class InvalidRefreshTokenError(AuthServiceError):
    """Ошибка невалидного refresh-токена."""


class PermissionDeniedError(AuthServiceError):
    """Ошибка недостаточных прав доступа."""


class RoleAlreadyExistsError(AuthServiceError):
    """Ошибка существующей роли."""


class RoleNotFoundError(AuthServiceError):
    """Ошибка отсутствующей роли."""


class PermissionAlreadyExistsError(AuthServiceError):
    """Ошибка существующего права доступа."""


class PermissionNotFoundError(AuthServiceError):
    """Ошибка отсутствующего права доступа."""
