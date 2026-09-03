"""Ошибки аутентификации и интеграции с Auth Service."""


class AuthIntegrationError(Exception):
    """Базовая ошибка интеграции с Auth Service."""


class InvalidAccessTokenError(AuthIntegrationError):
    """Access token отсутствует или невалиден."""


class AuthUserForbiddenError(AuthIntegrationError):
    """Пользователь неактивен или заблокирован."""


class AuthServiceUnavailableError(AuthIntegrationError):
    """Auth Service временно недоступен."""


class AuthServiceContractError(AuthIntegrationError):
    """Auth Service вернул неожиданный ответ."""
