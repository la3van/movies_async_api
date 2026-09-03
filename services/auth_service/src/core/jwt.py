"""Утилиты для работы с JWT access-токенами."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from core.config import get_settings
from jwt import InvalidTokenError

ACCESS_TOKEN_TYPE = "access"


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Проверенные claims access-токена."""

    user_id: UUID
    token_id: UUID
    session_id: UUID
    issued_at: datetime
    expires_at: datetime


def create_access_token(
    subject: str,
    session_id: UUID,
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
        additional_claims={
            "jti": str(uuid4()),
            "sid": str(session_id),
        },
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
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_jwt_token(token: str) -> dict[str, Any]:
    """Декодирует и валидирует JWT-токен."""
    settings = get_settings()

    return jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        options={
            "require": [
                "sub",
                "type",
                "iat",
                "exp",
                "jti",
                "sid",
            ],
        },
    )


def decode_access_token(
    token: str,
) -> AccessTokenClaims:
    """Декодирует acces-токен в типизированные claims."""
    payload = decode_jwt_token(token)

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError(
            "Invalid access token type",
        )

    try:
        return AccessTokenClaims(
            user_id=UUID(str(payload["sub"])),
            token_id=UUID(str(payload["jti"])),
            session_id=UUID(str(payload["sid"])),
            issued_at=_decode_numeric_date(
                payload["iat"],
            ),
            expires_at=_decode_numeric_date(
                payload["exp"],
            ),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        OverflowError,
    ) as error:
        raise InvalidTokenError(
            "Invalid access token claims",
        ) from error


def _decode_numeric_date(
    value: object,
) -> datetime:
    """Преобразует JWT NumericDate в UTC datetime."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(
            "Boolean is not a valid NumericDate",
        )

    return datetime.fromtimestamp(
        float(value),
        tz=timezone.utc,
    )
