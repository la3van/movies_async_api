"""Сервис аутентификации UGC Service."""

import logging

from auth.client import AuthServiceClient
from auth.exceptions import AuthServiceUnavailableError
from auth.jwt import decode_access_token
from auth.models import AuthenticatedUser
from core.config import Settings
from core.tracing import trace_method

logger = logging.getLogger(__name__)


class AuthenticationService:
    """Проверить JWT локально и подтвердить пользователя в Auth Service."""

    def __init__(self, client: AuthServiceClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @trace_method("ugc.auth.authenticate")
    async def authenticate(
        self,
        *,
        token: str,
        forwarded_headers: dict[str, str],
    ) -> AuthenticatedUser:
        claims = decode_access_token(token, self._settings)
        try:
            user = await self._client.get_current_user(
                token=token,
                forwarded_headers=forwarded_headers,
            )
        except AuthServiceUnavailableError:
            if not self._settings.auth_allow_jwt_fallback:
                raise
            logger.warning(
                "Auth Service unavailable; using verified access token claims",
                exc_info=True,
            )
            return AuthenticatedUser(
                id=claims.sub,
                login=claims.login,
                access_token=token,
            )

        if user.id != claims.sub:
            from auth.exceptions import AuthServiceContractError

            raise AuthServiceContractError(
                "Auth user id does not match JWT sub"
            )

        return AuthenticatedUser(
            id=user.id,
            login=user.login,
            access_token=token,
        )
