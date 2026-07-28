"""OAuth-адаптер Яндекс ID."""
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field, ValidationError

from oauth.base import OAuthProvider
from oauth.enums import OAuthProviderName
from oauth.models import OAuthToken, OAuthUserInfo
from services.exceptions import OAuthProviderResponseError
from oauth.providers.http import request_oauth_json

_AUTHORIZATION_URL = 'https://oauth.yandex.ru/authorize'
_TOKEN_URL = 'https://oauth.yandex.ru/token'
_USER_INFO_URL = 'https://login.yandex.ru/info'


class _YandexTokenResponse(BaseModel):
    """Внутренняя схема ответа Yandex token endpoint."""
    access_token: str = Field(min_length=1)
    token_type: str = 'bearer'
    expires_in: int | None = None
    refresh_token: str | None = None


class _YandexUserResponse(BaseModel):
    """Внутренняя схема профиля пользователя Яндекса."""
    id: str | int
    client_id: str | None = None
    login: str | None = None

    default_email: str | None = None
    emails: list[str] = Field(default_factory=list)

    first_name: str | None = None
    last_name: str | None = None


class YandexOAuthProvider(OAuthProvider):
    """Реализует OAuth Authorization Code Flow для Яндекса ID."""
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """Сохраняет конфигурацию OAuth-приложения."""
        if not client_id:
            raise ValueError(
                'Yandex OAuth client ID must not be empty',
            )

        if not client_secret:
            raise ValueError(
                'Yandex OAuth client secret must not be empty',
            )

        if not redirect_uri:
            raise ValueError(
                'Yandex OAuth redirect URI must not be empty',
            )

        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scopes = scopes.strip()
        self._http_client = http_client

    @property
    def name(self) -> OAuthProviderName:
        """Возвращает имя OAuth-провайдера."""
        return OAuthProviderName.YANDEX

    @property
    def redirect_uri(self) -> str:
        """Возвращает callback URL Яндекса."""
        return self._redirect_uri

    def build_authorization_url(
        self,
        *,
        state: str,
        code_challenge: str,
    ) -> str:
        """Формирует URL страницы авторизации Яндекса."""
        query_params = {
            'response_type': 'code',
            'client_id': self._client_id,
            'redirect_uri': self._redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
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
        """Обменивает authorization code на токен Яндекса."""
        _ = state

        if redirect_uri != self._redirect_uri:
            raise OAuthProviderResponseError(
                'Yandex OAuth redirect URI does not match',
            )

        request_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'code_verifier': code_verifier,
        }

        if device_id is not None:
            request_data['device_id'] = device_id

        payload = await request_oauth_json(
            client=self._http_client,
            method='POST',
            url=_TOKEN_URL,
            service_name='Yandex OAuth',
            data=request_data,
            auth=httpx.BasicAuth(
                username=self._client_id,
                password=self._client_secret,
            ),
        )

        try:
            token_response = _YandexTokenResponse.model_validate(
                payload,
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                'Yandex OAuth returned an invalid token response',
            ) from error

        return OAuthToken(
            access_token=token_response.access_token,
            token_type=token_response.token_type,
            expires_in=token_response.expires_in,
            refresh_token=token_response.refresh_token,
        )

    async def get_user_info(
        self,
        *,
        token: OAuthToken,
    ) -> OAuthUserInfo:
        """Получает и нормализует профиль пользователя Яндекса."""
        payload = await request_oauth_json(
            client=self._http_client,
            method='GET',
            url=_USER_INFO_URL,
            service_name='Yandex ID API',
            params={
                'format': 'json',
            },
            headers={
                'Authorization': (
                    f'OAuth {token.access_token}'
                ),
            },
        )

        try:
            user_response = _YandexUserResponse.model_validate(
                payload,
            )
        except ValidationError as error:
            raise OAuthProviderResponseError(
                'Yandex ID API returned an invalid user response',
            ) from error

        if (
            user_response.client_id is not None
            and user_response.client_id != self._client_id
        ):
            raise OAuthProviderResponseError(
                'Yandex token belongs to another OAuth client',
            )

        email = user_response.default_email

        if email is None and user_response.emails:
            email = user_response.emails[0]

        return OAuthUserInfo(
            provider_user_id=str(user_response.id),
            email=email,
            email_verified=None,
            login=user_response.login,
            first_name=user_response.first_name,
            last_name=user_response.last_name,
        )
