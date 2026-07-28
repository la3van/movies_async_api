"""OAuth-адаптер VK ID."""
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field, ValidationError

from oauth.base import OAuthProvider
from oauth.enums import OAuthProviderName
from oauth.providers.http import request_oauth_json
from oauth.models import OAuthToken, OAuthUserInfo
from services.exceptions import OAuthProviderResponseError

_AUTHORIZATION_URL = 'https://id.vk.ru/authorize'
_TOKEN_URL = 'https://id.vk.ru/oauth2/auth'
_USER_INFO_URL = 'https://id.vk.ru/oauth2/user_info'


class _VkTokenResponse(BaseModel):
    """Ответ VK ID token endpoint."""

    access_token: str = Field(min_length=1)
    expires_in: int | None = None
    refresh_token: str | None = None
    state: str = Field(min_length=1)
    token_type: str = 'Bearer'
    user_id: str | int | None = None
    scope: str | None = None
    id_token: str | None = None


class _VkUserData(BaseModel):
    """Данные пользователя внутри VK ID-ответа."""

    user_id: str | int
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class _VkUserInfoResponse(BaseModel):
    """Ответ VK ID user-info endpoint."""

    user: _VkUserData


class VkOAuthProvider(OAuthProvider):
    """Реализует OAuth 2.1-вход через VK ID."""
    def __init__(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        scopes: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Сохраняет настройки VK ID."""
        if not client_id:
            raise ValueError(
                'VK ID client ID must not be empty',
            )

        if not redirect_uri:
            raise ValueError(
                'VK ID redirect URI must not be empty',
            )

        self._client_id = client_id
        self._redirect_uri = redirect_uri
        self._scopes = scopes.strip()
        self._http_client = http_client

    @property
    def name(self) -> OAuthProviderName:
        """Возвращает имя провайдера."""
        return OAuthProviderName.VK

    @property
    def redirect_uri(self) -> str:
        """Возвращает callback URL VK ID."""
        return self._redirect_uri

    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        """Формирует VK ID authorization URL."""
        query_params = {
            'response_type': 'code',
            'client_id': self._client_id,
            'app_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 's256',
            'prompt': '',
        }

        if self._scopes:
            query_params['scope'] = self._scopes

        return (
            f'{_AUTHORIZATION_URL}'
            f'?{urlencode(query_params)}'
        )

    async def exchange_code(
        self,
        *,
        code: str,
        code_verifier: str,
        redirect_uri: str,
        state: str,
        device_id: str | None = None,
    ) -> OAuthToken:
        """Обменивает authorization code на VK ID token."""
        if redirect_uri != self._redirect_uri:
            raise OAuthProviderResponseError(
                'VK ID redirect URI does not match',
            )

        if not device_id:
            raise OAuthProviderResponseError(
                'VK ID callback does not contain device_id',
            )

        payload = await request_oauth_json(
            client=self._http_client,
            method='POST',
            url=_TOKEN_URL,
            service_name='VK ID OAuth',
            params={
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
                'client_id': self._client_id,
                'code_verifier': code_verifier,
                'state': state,
                'device_id': device_id,
            },
            data={
                'code': code,
            },
        )

        try:
            token_response = _VkTokenResponse.model_validate(
                payload,
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                'VK ID returned an invalid token response',
            ) from error

        if token_response.state != state:
            raise OAuthProviderResponseError(
                'VK ID token response contains invalid state',
            )

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
        """Получает нормализованный профиль VK ID."""
        payload = await request_oauth_json(
            client=self._http_client,
            method='POST',
            url=_USER_INFO_URL,
            service_name='VK ID UserInfo',
            params={
                'client_id': self._client_id,
            },
            data={
                'access_token': token.access_token,
            },
        )

        try:
            user_response = (
                _VkUserInfoResponse.model_validate(
                    payload,
                )
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                'VK ID returned an invalid user response',
            ) from error

        user = user_response.user

        return OAuthUserInfo(
            provider_user_id=str(user.user_id),
            email=user.email,
            email_verified=None,
            login=None,
            first_name=user.first_name,
            last_name=user.last_name,
        )
