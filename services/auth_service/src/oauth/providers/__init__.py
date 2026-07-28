"""Адаптеры внешних OAuth-провайдеров."""
from oauth.providers.google import GoogleOAuthProvider
from oauth.providers.vk import VkOAuthProvider
from oauth.providers.yandex import YandexOAuthProvider

__all__ = (
    'GoogleOAuthProvider',
    'VkOAuthProvider',
    'YandexOAuthProvider',
)
