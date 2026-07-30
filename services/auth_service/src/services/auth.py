"""Сервис аутентификации."""
from core.tracing import trace_method
from datetime import datetime, timezone
from uuid import UUID

from api.v1.schemas.auth import LoginRequest, RegisterRequest
from cache.base import Cache
from core.security import hash_password, hash_token, verify_password
from models.refresh_session import RefreshSession
from services.cache_keys.users import (
    get_login_history_cache_pattern,
)
from services.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from services.token import TokenPair, TokenService
from services.login_session import create_login_session
from unit_of_work.base import (
    AbstractUnitOfWork,
    UnitOfWorkFactory,
)
from token_revocation.base import AccessTokenRevocationStore


class AuthService:
    """Сервис регистрации, логина и управления refresh-сессиями."""
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        token_service: TokenService,
        cache: Cache,
        revocation_store: AccessTokenRevocationStore,
    ) -> None:
        """Инициализирует сервис аутентификации."""
        self._uow_factory = uow_factory
        self._token_service = token_service
        self._cache = cache
        self._revocation_store = revocation_store

    @trace_method("auth.register")
    async def register(
        self,
        register_data: RegisterRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Регистрирует пользователя и возвращает пару токенов."""
        async with self._uow_factory() as uow:
            existing_user = await uow.users.get_by_login(
                register_data.login,
            )
            if existing_user is not None:
                raise UserAlreadyExistsError(
                    'User with this login already exists',
                )

            existing_user = await uow.users.get_by_email(
                str(register_data.email),
            )
            if existing_user is not None:
                raise UserAlreadyExistsError(
                    'User with this email already exists',
                )

            user = await uow.users.create(
                login=register_data.login,
                email=str(register_data.email),
                password_hash=hash_password(
                    register_data.password,
                ),
                first_name=register_data.first_name,
                last_name=register_data.last_name,
            )

            default_roles = await uow.roles.get_default_roles()
            if default_roles:
                await uow.users.add_roles(
                    user,
                    default_roles,
                )

            user_with_roles = await uow.users.get_by_id(user.id)
            if user_with_roles is None:
                raise UserNotFoundError('User not found')

            token_pair = await create_login_session(
                uow=uow,
                token_service=self._token_service,
                user=user_with_roles,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await uow.commit()

        return token_pair

    @trace_method("auth.login")
    async def login(
        self,
        login_data: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Аутентифицирует пользователя и возвращает пару токенов."""
        async with self._uow_factory() as uow:
            user = await uow.users.get_by_login(
                login_data.login,
            )

            if user is None:
                await self._save_failed_login(
                    uow,
                    login=login_data.login,
                    reason='User not found',
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
                raise InvalidCredentialsError(
                    'Invalid login or password',
                )

            if not verify_password(
                login_data.password,
                user.password_hash,
            ):
                await self._save_failed_login(
                    uow,
                    login=login_data.login,
                    user_id=user.id,
                    reason='Invalid password',
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
                raise InvalidCredentialsError(
                    'Invalid login or password',
                )

            if not user.is_active:
                await self._save_failed_login(
                    uow,
                    login=login_data.login,
                    user_id=user.id,
                    reason='User is inactive',
                    user_agent=user_agent,
                    ip_address=ip_address,
                )
                raise InactiveUserError('User is inactive')

            token_pair = await create_login_session(
                uow=uow,
                token_service=self._token_service,
                user=user,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await uow.commit()

        await self._invalidate_login_history_cache(user.id)

        return token_pair

    @trace_method("auth.refresh")
    async def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Обновляет пару токенов через refresh-токен."""
        async with self._uow_factory() as uow:
            refresh_session = await self._get_valid_refresh_session(
                uow,
                refresh_token,
            )

            user = await uow.users.get_by_id(
                refresh_session.user_id,
            )
            if user is None or not user.is_active:
                raise InvalidRefreshTokenError(
                    'Invalid refresh token',
                )

            await uow.refresh_sessions.revoke(
                refresh_session,
            )

            token_pair, refresh_token_data = (
                self._token_service.create_token_pair(user)
            )

            await uow.refresh_sessions.create(
                session_id=refresh_token_data.session_id,
                user_id=user.id,
                token_hash=refresh_token_data.token_hash,
                expires_at=refresh_token_data.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            old_session_id = refresh_session.id

            await uow.commit()

        await self._revocation_store.revoke_sessions(
            [old_session_id],
        )

        return token_pair

    @trace_method("auth.logout")
    async def logout(self, refresh_token: str) -> None:
        """Завершает одну refresh-сессию."""
        async with self._uow_factory() as uow:
            refresh_session = await self._get_valid_refresh_session(
                uow,
                refresh_token,
            )

            session_id = refresh_session.id

            await uow.refresh_sessions.revoke(
                refresh_session,
            )

            await uow.commit()

        await self._revocation_store.revoke_sessions(
            [session_id],
        )

    @trace_method("auth.logout_others")
    async def logout_others(self, refresh_token: str) -> None:
        """Завершает все refresh-сессии пользователя, кроме текущей."""
        async with self._uow_factory() as uow:
            refresh_session = await self._get_valid_refresh_session(
                uow,
                refresh_token,
            )

            revoked_session_ids = (
                await uow.refresh_sessions
                .revoke_all_by_user_id(
                    user_id=refresh_session.user_id,
                    exclude_session_id=refresh_session.id,
                )
            )

            await uow.commit()

        await self._revocation_store.revoke_sessions(
            revoked_session_ids,
        )

    async def _save_failed_login(
        self,
        uow: AbstractUnitOfWork,
        *,
        login: str,
        user_id: UUID | None = None,
        reason: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Сохраняет неуспешную попытку входа."""
        await uow.login_history.create(
            user_id=user_id,
            login=login,
            is_successful=False,
            reason=reason,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        await uow.commit()

        if user_id is not None:
            await self._invalidate_login_history_cache(user_id)

    async def _get_valid_refresh_session(
        self,
        uow: AbstractUnitOfWork,
        refresh_token: str,
    ) -> RefreshSession:
        """Возвращает валидную refresh-сессию или выбрасывает ошибку."""
        token_hash = hash_token(refresh_token)

        refresh_session = (
            await uow.refresh_sessions.get_by_token_hash(
                token_hash,
            )
        )

        if refresh_session is None:
            raise InvalidRefreshTokenError(
                'Invalid refresh token',
            )

        if refresh_session.revoked_at is not None:
            raise InvalidRefreshTokenError(
                'Refresh token has been revoked',
            )

        if self._is_refresh_session_expired(refresh_session):
            raise InvalidRefreshTokenError(
                'Refresh token has expired',
            )

        return refresh_session

    @staticmethod
    def _is_refresh_session_expired(
        refresh_session: RefreshSession,
    ) -> bool:
        """Проверяет, истекла ли refresh-сессия."""
        expires_at = refresh_session.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc,
            )

        return expires_at <= datetime.now(timezone.utc)

    async def _invalidate_login_history_cache(
        self,
        user_id: UUID,
    ) -> None:
        """Инвалидирует все страницы истории входов пользователя."""
        await self._cache.delete_by_pattern(
            get_login_history_cache_pattern(user_id),
        )
