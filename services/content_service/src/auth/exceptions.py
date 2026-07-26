"""Исключение интеграции с Auth Service."""


class AuthIntegrationError(Exception):
    """Базовая ошибка интеграции."""


class InvalidAccessTokenError(AuthIntegrationError):
    """Access token отсутствует или невалиден."""


class AuthUserForbiddenError(AuthIntegrationError):
    """Пользователь заблокирован или неактивен."""


class AuthServiceUnavailableError(AuthIntegrationError):
    """Auth Service временно недоступен."""


class AuthServiceContractError(AuthIntegrationError):
    """Auth Service нарушил ожидаемый контракт."""
