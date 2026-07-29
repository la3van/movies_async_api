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


class InvalidOAuthStateError(AuthServiceError):
    """Ошибка отсутствующего, просроченного или неверного OAuth-state."""


class OAuthStateStorageError(AuthServiceError):
    """Ошибка хранилища OAuth-state."""


class OAuthProviderError(AuthServiceError):
    """Базовая ошибка внешнего OAuth-провайдера."""


class OAuthProviderUnavailableError(OAuthProviderError):
    """OAuth-провайдер недоступен по сети или вернил 5xx."""


class OAuthProviderResponseError(OAuthProviderError):
    """OAuth-провайдер отклонил запрос или вернул неверный ответ."""


class OAuthProviderNotConfiguredError(AuthServiceError):
    """Ошибка отсутствующей конфигурации OAuth-провайдера."""


class OAuthAuthorizationError(AuthServiceError):
    """OAuth-провайдер вернул ошибку вместо authorization code."""


class OAuthEmailRequiredError(AuthServiceError):
    """OAuth-провайдер не предоставил подходящий email."""


class OAuthAccountLinkRequiredError(AuthServiceError):
    """Email уже принадлежит локальному аккаунту."""


class InvalidLoginHistoryDateRangeError(AuthServiceError):
    """Начало диапазона истории не меньше его окончания."""
