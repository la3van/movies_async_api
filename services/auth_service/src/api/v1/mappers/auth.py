"""Преобразование моделей авторизации в схемы API."""

from api.v1.schemas.auth import TokenPairResponse
from services.token import TokenPair


def build_token_pair_response(token_pair: TokenPair) -> TokenPairResponse:
    """Преобразует DTO пары токенов в response-схему."""
    return TokenPairResponse(
        access_token=token_pair.access_token,
        refresh_token=token_pair.refresh_token,
        token_type=token_pair.token_type,
    )
