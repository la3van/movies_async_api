"""HTTP-клиент для Auth Service."""
import httpx
from pydantic import ValidationError

from auth.exceptions import (
    AuthServiceContractError,
    AuthServiceUnavailableError,
    AuthUserForbiddenError,
    InvalidAccessTokenError,
)
from auth.models import AuthenticatedUser


class AuthServiceClient:
    """Проверяет access-токен через существующий /users/me Auth Service."""
    def __init__(
        self,
        client: httpx.Client,
    ) -> None:
        """Создать клиент Auth Service."""
        self._client = client

    def get_current_user(
        self,
        *,
        authorization: str,
        request_id: str,
    ) -> AuthenticatedUser:
        """Проверить access-токен и вернуть текущего пользователя."""
        try:
            response = self._client.get(
                "users/me",
                headers={
                    "Authorization": authorization,
                    "X-Request-ID": request_id,
                },
            )
        except httpx.RequestError as exc:
            raise AuthServiceUnavailableError(
                "Auth Service is unavailable"
            ) from exc

        if response.status_code in {401, 404}:
            raise InvalidAccessTokenError(
                "Auth Service rejected access token"
            )

        if response.status_code == 403:
            raise AuthUserForbiddenError(
                "Auth Service rejected user"
            )

        if (
            response.status_code == 408
            or response.status_code == 429
            or response.status_code >= 500
        ):
            raise AuthServiceUnavailableError(
                "Auth Service is temporarily unavailable"
            )

        if response.status_code != 200:
            raise AuthServiceContractError(
                "Unexpected Auth Service status: "
                f"{response.status_code}"
            )

        try:
            return AuthenticatedUser.model_validate(
                response.json(),
            )
        except (ValueError, ValidationError) as exc:
            raise AuthServiceContractError(
                "Invalid Auth Service response"
            ) from exc

    def close(self) -> None:
        """Закрыть HTTP-клиент."""
        self._client.close()
