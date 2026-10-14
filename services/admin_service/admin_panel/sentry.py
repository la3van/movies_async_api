"""Настройка мониторинга ошибок Django через Sentry."""

import logging
import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def _get_sample_rate(name: str) -> float:
    """Прочитать и ограничить коэффициент сэмплирования диапазоном 0..1."""
    try:
        value = float(os.getenv(name, "0"))
    except ValueError:
        return 0.0

    return min(max(value, 0.0), 1.0)


def init_sentry(*, service_name: str) -> bool:
    """Инициализировать Sentry, если задан DSN."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "local"),
        release=os.getenv("SENTRY_RELEASE") or None,
        traces_sample_rate=_get_sample_rate(
            "SENTRY_TRACES_SAMPLE_RATE",
        ),
        profiles_sample_rate=_get_sample_rate(
            "SENTRY_PROFILES_SAMPLE_RATE",
        ),
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        integrations=[
            DjangoIntegration(transaction_style="url"),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
    )
    sentry_sdk.set_tag("service.name", service_name)
    return True
