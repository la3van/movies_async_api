"""Реестр доступных OAuth-провайдеров."""

from collections.abc import Iterable

from oauth.base import OAuthProvider
from oauth.enums import OAuthProviderName
from services.exceptions import (
    OAuthProviderNotConfiguredError,
)


class OAuthProviderRegistry:
    """Хранит настроение OAuth-провайдера."""

    def __init__(
        self,
        providers: Iterable[OAuthProvider],
    ) -> None:
        """Создаёт отображение имени провайдера на его адаптер."""
        self._providers: dict[
            OAuthProviderName,
            OAuthProvider,
        ] = {}

        for provider in providers:
            if provider.name in self._providers:
                raise ValueError(
                    "OAuth provider is registered more than once: "
                    f"{provider.name.value}",
                )

            self._providers[provider.name] = provider

    def get(
        self,
        provider_name: OAuthProviderName,
    ) -> OAuthProvider:
        """Возвращает настроенный OAuth-провайдер."""
        provider = self._providers.get(provider_name)

        if provider is None:
            raise OAuthProviderNotConfiguredError(
                f"OAuth provider is not configured: {provider_name.value}"
            )

        return provider
