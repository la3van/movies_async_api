"""Перечисления OAuth-модуля."""

from enum import Enum


class OAuthProviderName(str, Enum):
    """Поддерживаемые OAuth-провайдеры."""

    YANDEX = "yandex"
    VK = "vk"
    GOOGLE = "google"
