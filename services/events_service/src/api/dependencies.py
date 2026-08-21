"""Получение зависимостей HTTP API."""
from typing import cast

from flask import current_app

from auth.client import AuthServiceClient
from core.event_rate_limit import EventRateLimiter
from services.events import EventService


def get_event_service() -> EventService:
    """Получить сервис обработки пользовательских событий."""
    return cast(
        EventService,
        current_app.extensions["event_service"],
    )


def get_auth_client() -> AuthServiceClient:
    """Получить клиент Auth Service."""
    return cast(
        AuthServiceClient,
        current_app.extensions["auth_client"],
    )


def get_event_rate_limiter() -> EventRateLimiter:
    """Получить rate limiter пользовательских событий."""
    return cast(
        EventRateLimiter,
        current_app.extensions["event_rate_limiter"],
    )
