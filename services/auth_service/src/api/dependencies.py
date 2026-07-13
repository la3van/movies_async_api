"""FastAPI dependencies auth-сервиса."""
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.users import UserResponse
from cache.redis import RedisCache
from core.config import get_settings
from core.jwt import ACCESS_TOKEN_TYPE, decode_jwt_token
from db.postgres import get_session
from db.redis import get_redis
from repositories.postgres.login_history import PostgresLoginHistoryRepository
from repositories.postgres.permission import PostgresPermissionRepository
from repositories.postgres.refresh_session import (
    PostgresRefreshSessionRepository
)
from repositories.postgres.role import PostgresRoleRepository
from repositories.postgres.user import PostgresUserRepository
from services.auth import AuthService
from services.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    PermissionDeniedError,
)
from services.permission import PermissionService
from services.role import RoleService
from services.token import TokenService
from services.user import UserService


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl='/api/v1/auth/login',
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Возвращает SQLAlchemy-сессию."""
    async for session in get_session():
        yield session


async def get_redis_cache(
    redis: Redis = Depends(get_redis),
) -> RedisCache:
    """Возвращает Redis-кеш."""
    return RedisCache(redis)


async def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_redis_cache),
) -> AuthService:
    """Возвращает сервис аутентификации."""
    return AuthService(
        session=session,
        user_repository=PostgresUserRepository(session),
        role_repository=PostgresRoleRepository(session),
        refresh_session_repository=PostgresRefreshSessionRepository(session),
        login_history_repository=PostgresLoginHistoryRepository(session),
        token_service=TokenService(),
        cache=cache,
    )


async def get_user_service(
    session: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_redis_cache),
) -> UserService:
    """Возвращает сервис пользователей."""
    settings = get_settings()

    return UserService(
        session=session,
        user_repository=PostgresUserRepository(session),
        role_repository=PostgresRoleRepository(session),
        login_history_repository=PostgresLoginHistoryRepository(session),
        refresh_session_repository=PostgresRefreshSessionRepository(session),
        cache=cache,
        user_cache_ttl=settings.user_cache_expire_in_seconds,
        login_history_cache_ttl=settings.login_history_cache_expire_in_seconds,
    )


async def get_permission_service(
    session: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_redis_cache),
) -> PermissionService:
    """Возвращает сервис прав доступа."""
    settings = get_settings()

    return PermissionService(
        session=session,
        permission_repository=PostgresPermissionRepository(session),
        cache=cache,
        permission_cache_ttl=settings.permission_cache_expire_in_seconds,
    )


async def get_role_service(
    session: AsyncSession = Depends(get_db_session),
    cache: RedisCache = Depends(get_redis_cache),
) -> RoleService:
    """Возвращает сервис ролей."""
    settings = get_settings()

    permission_service = PermissionService(
        session=session,
        permission_repository=PostgresPermissionRepository(session),
        cache=cache,
        permission_cache_ttl=settings.permission_cache_expire_in_seconds,
    )

    return RoleService(
        session=session,
        role_repository=PostgresRoleRepository(session),
        permission_service=permission_service,
        cache=cache,
        role_cache_ttl=settings.role_cache_expire_in_seconds,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Возвращает текущего пользователя по JWT access-token."""
    try:
        payload = decode_jwt_token(token)

        if payload.get('type') != ACCESS_TOKEN_TYPE:
            raise InvalidCredentialsError('Invalid token type')

        user_id = UUID(str(payload.get('sub')))
    except (ExpiredSignatureError, InvalidTokenError, ValueError) as error:
        raise InvalidCredentialsError(
            'Could not validate credentials',
        ) from error

    return await user_service.get_by_id(user_id)


async def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Возвращает текущего активного пользователя."""
    if not current_user.is_active:
        raise InactiveUserError('User is inactive')

    return current_user


async def require_superuser(
    current_user: UserResponse = Depends(get_current_active_user),
) -> UserResponse:
    """Проверяет, что текущий пользователь является суперпользователем."""
    if not current_user.is_superuser:
        raise PermissionDeniedError('Not enough permissions')

    return current_user


def get_request_user_agent(request: Request) -> str | None:
    """Возвращает User-Agent из запроса."""
    return request.headers.get('user-agent')


def get_request_ip_address(request: Request) -> str | None:
    """Возвращает IP-адрес клиента из запроса."""
    if request.client is None:
        return None

    return request.client.host
