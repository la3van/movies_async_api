"""Локальная проверка access JWT."""
import jwt
from jwt import InvalidTokenError
from pydantic import ValidationError

from auth.exceptions import InvalidAccessTokenError
from auth.models import AccessTokenClaims
from core.config import Settings


def decode_access_token(
    token: str,
    settings: Settings,
) -> AccessTokenClaims:
    """Проверяет подпись JWT и возвращает его claims."""
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.jwt_secret_key,
            algorithms=[
                settings.jwt_algorithm,
            ],
            options={
                'require': [
                    'sub',
                    'type',
                    'iat',
                    'exp',
                ],
            },
        )

        return AccessTokenClaims.model_validate(payload)
    except (InvalidTokenError, ValidationError) as error:
        raise InvalidAccessTokenError(
            'Invalid access token',
        ) from error
