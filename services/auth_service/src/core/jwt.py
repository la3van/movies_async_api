"""Утилиты для работы с JWT access-токенами."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from core.config import get_settings

ACCESS_TOKEN_TYPE = 'access'


def create_access_token(
    subject: str,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Создаёт JWT access-token."""
    settings = get_settings()

    expires_delta = timedelta(
        minutes=settings.access_token_expire_minutes,
    )

    return create_jwt_token(
        subject=subject,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta,
        additional_claims=additional_claims,
    )


def create_jwt_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Создаёт JWT-токен."""
    settings = get_settings()

    now = datetime.now(timezone.utc)

    payload: dict[str, Any] = {
        'sub': subject,
        'type': token_type,
        'iat': now,
        'exp': now + expires_delta,
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT-токен."""
    settings = get_settings()

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
