"""Сервис аутентификации UGC Service."""

from auth.client import AuthServiceClient
from auth.models import AuthenticatedUser
from core.tracing import trace_method


class AuthenticationService:
    """Подтвердить пользователя через Auth Service."""

    def __init__(self, client: AuthServiceClient) -> None:
        self._client = client

    @trace_method("ugc.auth.authenticate")
    async def authenticate(
        self,
        *,
        token: str,
        forwarded_headers: dict[str, str],
    ) -> AuthenticatedUser:
        user = await self._client.get_current_user(
            token=token,
            forwarded_headers=forwarded_headers,
        )

        return AuthenticatedUser(
            id=user.id,
            login=user.login,
            access_token=token,
        )
