"""Функции конфигурации Django Debug Toolbar."""

from django.conf import settings
from django.http import HttpRequest


def show_toolbar(
    request: HttpRequest,
) -> bool:
    """Показывает toolbar только в разрешённом debug-режиме."""
    del request

    return bool(settings.DEBUG and settings.ENABLE_DEBUG_TOOLBAR)
