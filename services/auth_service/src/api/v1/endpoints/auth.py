"""Эндпоинты аутентификации."""
from fastapi import APIRouter, Depends, Request, status

from api.dependencies import (
    get_auth_service,
    get_request_ip_address,
    get_request_user_agent,
)
from api.v1.mappers.auth import build_token_pair_response
from api.v1.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenPairResponse,
)
from services.auth import AuthService
from core.rate_limit import rate_limit

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post(
    '/register',
    response_model=TokenPairResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            rate_limit(
                scope='auth:register',
                requests=3,
                window_seconds=60,
            ),
        ),
    ],
    summary='Регистрация пользователя',
    description=(
        'Создаёт нового пользователя в auth-сервисе, '
        'сохраняет первую login-сессию и возвращает '
        'пару JWT-токенов: access и refresh.'
    ),
    response_description=(
        'Пара access и refresh токенов нового пользователя'
    ),
)
async def register(
    register_data: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> TokenPairResponse:
    """Регистрирует пользователя и возвращает пару токенов."""
    token_pair = await auth_service.register(
        register_data=register_data,
        user_agent=get_request_user_agent(request),
        ip_address=get_request_ip_address(request),
    )
    return build_token_pair_response(token_pair)


@router.post(
    '/login',
    response_model=TokenPairResponse,
    dependencies=[
        Depends(
            rate_limit(
                scope='auth:login',
                requests=5,
                window_seconds=60,
            ),
        ),
    ],
    summary='Вход пользователя',
    description=(
        'Аутентифицирует пользователя по логину и паролю, '
        'создаёт refresh-сессию и возвращает пару JWT-токенов.'
    ),
    response_description='Пара access и refresh токенов',
)
async def login(
    login_data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> TokenPairResponse:
    """Аутентифицирует пользователя и возвращает пару токенов."""
    token_pair = await auth_service.login(
        login_data=login_data,
        user_agent=get_request_user_agent(request),
        ip_address=get_request_ip_address(request),
    )
    return build_token_pair_response(token_pair)


@router.post(
    '/refresh',
    response_model=TokenPairResponse,
    dependencies=[
        Depends(
            rate_limit(
                scope='auth:refresh',
                requests=10,
                window_seconds=60,
            ),
        ),
    ],
    summary='Обновление токенов',
    description=(
        'Принимает refresh-токен, проверяет его валидность, '
        'отзывает старую refresh-сессию, создаёт новую '
        'и возвращает новую пару JWT-токенов.'
    ),
    response_description='Новая пара access и refresh токенов',
)
async def refresh_tokens(
    refresh_data: RefreshTokenRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> TokenPairResponse:
    """Обновляет пару токенов по refresh-токену."""
    token_pair = await auth_service.refresh(
        refresh_token=refresh_data.refresh_token,
        user_agent=get_request_user_agent(request),
        ip_address=get_request_ip_address(request),
    )
    return build_token_pair_response(token_pair)


@router.post(
    '/logout',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Выход из аккаунта',
    description=(
        'Отзывает текущую refresh-сессию пользователя. '
        'После этого соответствующий refresh-токен '
        'больше нельзя использовать для обновления токенов.'
    ),
    response_description='Пользователь успешно вышел из аккаунта',
)
async def logout(
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> None:
    """Завершает текущую refresh-сессию пользователя."""
    await auth_service.logout(refresh_token=logout_data.refresh_token)


@router.post(
    '/logout-others',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Выход из остальных аккаунтов',
    description=(
        'Отзывает все refresh-сессии пользователя, кроме текущей. '
        'Используется для реализации сценария '
        '"Выйти из остальных аккаунтов".'
    ),
    response_description='Все остальные refresh-сессии пользователя отозваны',
)
async def logout_others(
    logout_data: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),  # noqa: B008
) -> None:
    """Отзывает все refresh-сессии пользователя, кроме текущей."""
    await auth_service.logout_others(
        refresh_token=logout_data.refresh_token,
    )
