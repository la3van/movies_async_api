"""Базовый контракт OAuth-провайдера."""
from abc import ABC, abstractmethod

from oauth.enums import OAuthProviderName
from oauth.models import OAuthToken, OAuthUserInfo


class OAuthProvider(ABC):
    """Определяет общий контракт внешнего OAuth-провайдера."""
    @property
    @abstractmethod
    def name(self) -> OAuthProviderName:
        """Возвращает имя провайдера."""
        pass  # pragma: no cover

    @property
    @abstractmethod
    def redirect_uri(self) -> str:
        """Возвращает callback URL провайдера."""
        pass  # pragma: no cover

    @abstractmethod
    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        """Формирует URL страницы авторизации провайдера."""
        pass  # pragma: no cover

    @abstractmethod
    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        state: str,
        device_id: str | None = None,
    ) -> OAuthToken:
        """Обменивает authorization code на токен провайдера."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_user_info(
        self,
        *,
        token: OAuthToken,
    ) -> OAuthUserInfo:
        """Получает и нормализует профиль пользователя."""
        pass  # pragma: no cover
