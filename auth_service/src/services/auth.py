"""Сервис аутентификации."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.auth import LoginRequest, RegisterRequest
from core.security import hash_password, hash_token, verify_password
from models.refresh_session import RefreshSession
from repositories.interfaces.login_history import LoginHistoryRepository
from repositories.interfaces.refresh_session import RefreshSessionRepository
from repositories.interfaces.role import RoleRepository
from repositories.interfaces.user import UserRepository
from services.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    UserAlreadyExistsError,
)
from services.token import TokenPair, TokenService


class AuthService:
    """Сервис регистрации, логина и управления refresh-сессиями."""
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        role_repository: RoleRepository,
        refresh_session_repository: RefreshSessionRepository,
        login_history_repository: LoginHistoryRepository,
        token_service: TokenService,
    ) -> None:
        """Инициализирует сервис аутентификации."""
        self._session = session
        self._user_repository = user_repository
        self._role_repository = role_repository
        self._refresh_session_repository = refresh_session_repository
        self._login_history_repository = login_history_repository
        self._token_service = token_service

    async def register(
        self,
        register_data: RegisterRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Регистрирует пользователя и возвращает пару токенов."""
        existing_user = await self._user_repository.get_by_login(
            register_data.login,
        )
        if existing_user is not None:
            raise UserAlreadyExistsError('User with this login already exists')

        existing_user = await self._user_repository.get_by_email(
            str(register_data.email),
        )
        if existing_user is not None:
            raise UserAlreadyExistsError('User with this email already exists')

        try:
            user = await self._user_repository.create(
                login=register_data.login,
                email=str(register_data.email),
                password_hash=hash_password(register_data.password),
                first_name=register_data.first_name,
                last_name=register_data.last_name,
            )

            default_roles = await self._role_repository.get_default_roles()
            if default_roles:
                user = await self._user_repository.add_roles(
                    user, default_roles
                )

            token_pair, refresh_token_data = (
                self._token_service.create_token_pair(user)
            )

            await self._refresh_session_repository.create(
                user_id=user.id,
                token_hash=refresh_token_data.token_hash,
                expires_at=refresh_token_data.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await self._login_history_repository.create(
                user_id=user.id,
                login=user.login,
                is_successful=True,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await self._session.commit()

            return token_pair
        except Exception:
            await self._session.rollback()
            raise

    async def login(
        self,
        login_data: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Аутентифицирует пользователя и возвращает пару токенов."""
        user = await self._user_repository.get_by_login(login_data.login)

        if user is None:
            await self._save_failed_login(
                login=login_data.login,
                reason='User not found',
                user_agent=user_agent,
                ip_address=ip_address,
            )
            raise InvalidCredentialsError('Invalid login or password')

        if not verify_password(login_data.password, user.password_hash):
            await self._save_failed_login(
                login=login_data.login,
                user_id=user.id,
                reason='Invalid password',
                user_agent=user_agent,
                ip_address=ip_address,
            )
            raise InvalidCredentialsError('Invalid login or password')

        if not user.is_active:
            await self._save_failed_login(
                login=login_data.login,
                user_id=user.id,
                reason='User is inactive',
                user_agent=user_agent,
                ip_address=ip_address,
            )
            raise InactiveUserError('User is inactive')

        try:
            token_pair, refresh_token_data = (
                self._token_service.create_token_pair(user)
            )

            await self._refresh_session_repository.create(
                user_id=user.id,
                token_hash=refresh_token_data.token_hash,
                expires_at=refresh_token_data.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await self._login_history_repository.create(
                user_id=user.id,
                login=user.login,
                is_successful=True,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await self._session.commit()

            return token_pair
        except Exception:
            await self._session.rollback()
            raise

    async def refresh(
        self,
        refresh_token: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TokenPair:
        """Обновляет пару токенов через refresh-токен."""
        refresh_session = await self._get_valid_refresh_session(refresh_token)

        user = await self._user_repository.get_by_id(refresh_session.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError('Invalid refresh token')

        try:
            await self._refresh_session_repository.revoke(refresh_session)

            token_pair, refresh_token_data = (
                self._token_service.create_token_pair(user)
            )

            await self._refresh_session_repository.create(
                user_id=user.id,
                token_hash=refresh_token_data.token_hash,
                expires_at=refresh_token_data.expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )

            await self._session.commit()

            return token_pair
        except Exception:
            await self._session.rollback()
            raise

    async def logout(self, refresh_token: str) -> None:
        """Завершает одну refresh-сессию."""
        refresh_session = await self._get_valid_refresh_session(refresh_token)

        try:
            await self._refresh_session_repository.revoke(refresh_session)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def logout_others(self, refresh_token: str) -> None:
        """Завершает все refresh-сессии пользователя, кроме текущей."""
        refresh_session = await self._get_valid_refresh_session(refresh_token)

        try:
            await self._refresh_session_repository.revoke_all_by_user_id(
                user_id=refresh_session.user_id,
                exclude_session_id=refresh_session.id,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def _save_failed_login(
        self,
        *,
        login: str,
        user_id: UUID | None = None,
        reason: str | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Сохраняет неуспешную попытку входа."""
        try:
            await self._login_history_repository.create(
                user_id=user_id,
                login=login,
                is_successful=False,
                reason=reason,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def _get_valid_refresh_session(
        self,
        refresh_token: str,
    ) -> RefreshSession:
        """Возвращает валидную refresh-сессию или выбрасывает ошибку."""
        token_hash = hash_token(refresh_token)

        refresh_session = (
            await self._refresh_session_repository
            .get_by_token_hash(token_hash)
        )

        if refresh_session is None:
            raise InvalidRefreshTokenError('Invalid refresh token')

        if refresh_session.revoked_at is not None:
            raise InvalidRefreshTokenError('Refresh token has been revoked')

        if self._is_refresh_session_expired(refresh_session):
            raise InvalidRefreshTokenError('Refresh token has expired')

        return refresh_session

    @staticmethod
    def _is_refresh_session_expired(
        refresh_session: RefreshSession,
    ) -> bool:
        """Проверяет, истекла ли refresh-сессия."""
        expires_at = refresh_session.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return expires_at <= datetime.now(timezone.utc)
