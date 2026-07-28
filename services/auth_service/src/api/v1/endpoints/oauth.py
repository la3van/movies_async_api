"""Эндпоинты социальной OAuth-аутентификации."""
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Request,
    status,
)
from fastapi.responses import RedirectResponse

from api.dependencies import (
    get_oauth_service,
    get_request_ip_address,
    get_request_user_agent,
)
from api.v1.mappers.auth import build_token_pair_response
from api.v1.schemas.auth import TokenPairResponse
from core.rate_limit import rate_limit
from oauth.enums import OAuthProviderName
from services.exceptions import (
    InvalidOAuthStateError,
    OAuthAuthorizationError,
)
from services.oauth import OAuthService

router = APIRouter(
    prefix='/auth/oauth',
    tags=['oauth'],
)


@router.get(
    '/{provider}/login',
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
    dependencies=[
        Depends(
            rate_limit(
                scope='auth:oauth:login',
                requests=10,
                window_seconds=60,
            ),
        ),
    ],
    summary='Начало входа через OAuth-провайдера',
    description=(
        'Создаёт одноразовое OAuth-состояние с PKCE '
        'и перенаправляет пользователя на страницу '
        'авторизации выбранного провайдера.'
    ),
)
async def oauth_login(
    provider: OAuthProviderName,
    oauth_service: OAuthService = Depends(
        get_oauth_service,
    ),
) -> RedirectResponse:
    """Перенаправляет пользователя к OAuth-провайдеру."""
    authorization_url = (
        await oauth_service.start_authorization(
            provider_name=provider,
        )
    )

    return RedirectResponse(
        url=authorization_url,
        status_code=status.HTTP_302_FOUND,
    )


@router.get(
    '/{provider}/callback',
    response_model=TokenPairResponse,
    dependencies=[
        Depends(
            rate_limit(
                scope='auth:oauth:callback',
                requests=30,
                window_seconds=60,
            ),
        ),
    ],
    summary='Завершение входа через OAuth-провайдера',
    description=(
        'Проверяет одноразовый state, обменивает '
        'authorization code на токен провайдера, '
        'находит или создаёт пользователя и возвращает '
        'локальные access и refresh токены.'
    ),
)
async def oauth_callback(
    provider: OAuthProviderName,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(
        default=None,
    ),
    device_id: str | None = Query(default=None),
    oauth_service: OAuthService = Depends(
        get_oauth_service,
    ),
) -> TokenPairResponse:
    """Заврешает OAuth-вход."""
    if error is not None:
        message = f'OAuth authorization failed: {error}'
        if error_description:
            message = (
                f'{message}. '
                f'{error_description}'
            )

        raise OAuthAuthorizationError(message)

    if code is None:
        raise OAuthAuthorizationError(
            'OAuth callback does not contain authorization code',
        )

    if state is None:
        raise InvalidOAuthStateError(
            'OAuth callback does not contain state',
        )

    token_pair = await oauth_service.authenticate(
        provider_name=provider,
        code=code,
        state=state,
        device_id=device_id,
        user_agent=get_request_user_agent(request),
        ip_address=get_request_ip_address(request),
    )

    return build_token_pair_response(
        token_pair,
    )
