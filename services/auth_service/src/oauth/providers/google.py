"""OAuth-адаптер Google OpenID Connect."""

from urllib.parse import urlencode

import httpx
from oauth.base import OAuthProvider
from oauth.enums import OAuthProviderName
from oauth.models import OAuthToken, OAuthUserInfo
from oauth.providers.http import request_oauth_json
from pydantic import BaseModel, Field, ValidationError
from services.exceptions import OAuthProviderResponseError

_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_USER_INFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class _GoogleTokenResponse(BaseModel):
    """Ответ Google token endpoint."""

    access_token: str = Field(min_length=1)
    token_type: str = "Bearer"
    expires_in: int | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    scope: str | None = None


class _GoogleUserInfoResponse(BaseModel):
    """Профиль пользователя Google."""

    sub: str = Field(min_length=1)
    email: str | None = None
    email_verified: bool | None = None
    given_name: str | None = None
    family_name: str | None = None


class GoogleOAuthProvider(OAuthProvider):
    """Реализует OAuth/OIDC-вход через Google."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Сохраняет настройки Google OAuth."""
        if not client_id:
            raise ValueError(
                "Google OAuth client ID must not be empty",
            )

        if not client_secret:
            raise ValueError(
                "Google OAuth client secret must not be empty",
            )

        if not redirect_uri:
            raise ValueError(
                "Google OAuth redirect URI must not be empty",
            )

        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = scopes.strip()
        self._http_client = http_client

    @property
    def name(self) -> OAuthProviderName:
        """Возвращает имя провайдера."""
        return OAuthProviderName.GOOGLE

    @property
    def redirect_uri(self) -> str:
        """Возвращает callback URL Google."""
        return self._redirect_uri

    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        """Формирует Google authorization URL."""
        query_params = {
            "response_type": "code",
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "scope": self._scopes,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        return f"{_AUTHORIZATION_URL}?{urlencode(query_params)}"

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        state: str,
        device_id: str | None = None,
    ) -> OAuthToken:
        """Обменивает authorization code на Google token."""
        _ = state, device_id

        if redirect_uri != self._redirect_uri:
            raise OAuthProviderResponseError(
                "Google OAuth redirect URI does not match",
            )

        payload = await request_oauth_json(
            client=self._http_client,
            method="POST",
            url=_TOKEN_URL,
            service_name="Google OAuth",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
            },
        )

        try:
            token_response = _GoogleTokenResponse.model_validate(
                payload,
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                "Google returned an invalid token response",
            ) from error

        return OAuthToken(
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            refresh_token=token_response.refresh_token,
            id_token=token_response.id_token,
        )

    async def get_user_info(
        self,
        *,
        token: OAuthToken,
    ) -> OAuthUserInfo:
        """Получает нормализованный профиль Google."""
        payload = await request_oauth_json(
            client=self._http_client,
            method="GET",
            url=_USER_INFO_URL,
            service_name="Google UserInfo",
            headers={
                "Authorization": (f"Bearer {token.access_token}"),
            },
        )

        try:
            user_response = _GoogleUserInfoResponse.model_validate(
                payload,
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                "Google returned an invalid user response",
            ) from error

        return OAuthUserInfo(
            provider_user_id=user_response.sub,
            email=user_response.email,
            email_verified=(user_response.email_verified),
            login=None,
            first_name=user_response.given_name,
            last_name=user_response.family_name,
        )
