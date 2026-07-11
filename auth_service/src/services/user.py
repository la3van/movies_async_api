"""Сервис работы с пользователями."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.login_history import LoginHistoryResponse
from api.v1.schemas.users import UserPasswordUpdate, UserResponse, UserUpdate
from cache.base import Cache
from core.security import hash_password, verify_password
from repositories.interfaces.login_history import LoginHistoryRepository
from repositories.interfaces.refresh_session import RefreshSessionRepository
from repositories.interfaces.user import UserRepository
from services.cache_keys.users import (
    get_login_history_cache_key,
    get_user_cache_key,
)
from services.exceptions import InvalidCredentialsError, UserNotFoundError


class UserService:
    """Сервис пользовательских сценариев."""
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        login_history_repository: LoginHistoryRepository,
        refresh_session_repository: RefreshSessionRepository,
        cache: Cache,
        user_cache_ttl: int,
        login_history_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис пользователей."""
        self._session = session
        self._user_repository = user_repository
        self._login_history_repository = login_history_repository
        self._refresh_session_repository = refresh_session_repository
        self._cache = cache
        self._user_cache_ttl = user_cache_ttl
        self._login_history_cache_ttl = login_history_cache_ttl

    async def get_by_id(self, user_id: UUID) -> UserResponse:
        """Возвращает пользователя по идентификатору."""
        user_cache_key = get_user_cache_key(user_id)

        user = await self._cache.get_model(
            key=user_cache_key,
            model_type=UserResponse,
        )
        if user is not None:
            return user

        user_model = await self._user_repository.get_by_id(user_id)
        if user_model is None:
            raise UserNotFoundError('User not found')

        user = UserResponse.model_validate(user_model)

        await self._cache.set_model(
            key=user_cache_key,
            value=user,
            ttl=self._user_cache_ttl,
        )

        return user

    async def update_profile(
        self,
        user_id: UUID,
        user_data: UserUpdate,
    ) -> UserResponse:
        """Обновляет профиль пользователя."""
        user_model = await self._user_repository.get_by_id(user_id)
        if user_model is None:
            raise UserNotFoundError('User not found')

        fields_set = user_data.model_fields_set

        if 'first_name' in fields_set:
            user_model.first_name = user_data.first_name
        if 'last_name' in fields_set:
            user_model.last_name = user_data.last_name

        try:
            user_model = await self._user_repository.save(user_model)
            await self._session.commit()

            user = UserResponse.model_validate(user_model)

            await self._cache.delete(get_user_cache_key(user_id))
            await self._cache.set_model(
                keey=get_user_cache_key(user_id),
                value=user,
                ttl=self._user_cache_ttl,
            )

            return user
        except Exception:
            await self._session.rollback()
            raise

    async def change_password(
        self,
        user_id: UUID,
        password_data: UserPasswordUpdate,
    ) -> None:
        """Меняет пароль пользователя и отзывает refresh-сессии."""
        user_model = await self._user_repository.get_by_id(user_id)
        if user_model is None:
            raise UserNotFoundError('User not found')

        if not verify_password(
            password_data.old_password,
            password_data.new_password,
        ):
            raise InvalidCredentialsError('Invalid old password')

        try:
            user_model.password_hash = hash_password(
                password_data.new_password,
            )

            await self._user_repository.save(user_model)
            await self._refresh_session_repository.revoke_all_by_user_id(
                user_id,
            )

            await self._session.commit()

            await self._cache.delete(get_user_cache_key(user_id))
        except Exception:
            await self._session.rollback()
            raise

    async def get_login_history(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LoginHistoryResponse]:
        """Возвращает историю входов пользователя."""
        login_history_cache_key = get_login_history_cache_key(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        login_history = await self._cache.get_models(
            key=login_history_cache_key,
            model_type=LoginHistoryResponse,
        )
        if login_history is not None:
            return login_history

        user_model = await self._user_repository.get_by_id(user_id)
        if user_model is None:
            raise UserNotFoundError('User not found')

        login_history_models = (
            await self._login_history_repository.get_by_user_id(
                user_id,
                limit=limit,
                offset=offset,
            )
        )
        login_history = [
            LoginHistoryResponse.model_validate(history_record)
            for history_record in login_history_models
        ]

        await self._cache.set_models(
            key=login_history_cache_key,
            values=login_history,
            ttl=self._login_history_cache_ttl,
        )

        return login_history
