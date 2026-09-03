"""Сервис работы с пользователями."""

from datetime import datetime, timezone
from uuid import UUID

from api.v1.schemas.login_history import LoginHistoryResponse
from api.v1.schemas.users import (
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)
from cache.base import Cache
from core.security import hash_password, verify_password
from core.tracing import trace_method
from services.cache_keys.users import (
    get_login_history_cache_key,
    get_user_cache_key,
)
from services.exceptions import (
    InvalidCredentialsError,
    InvalidLoginHistoryDateRangeError,
    RoleNotFoundError,
    UserNotFoundError,
)
from token_revocation.base import AccessTokenRevocationStore
from unit_of_work.base import UnitOfWorkFactory


class UserService:
    """Сервис пользовательских сценариев."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        cache: Cache,
        revocation_store: AccessTokenRevocationStore,
        user_cache_ttl: int,
        login_history_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис пользователей."""
        self._uow_factory = uow_factory
        self._cache = cache
        self._revocation_store = revocation_store
        self._user_cache_ttl = user_cache_ttl
        self._login_history_cache_ttl = login_history_cache_ttl

    @trace_method("users.get_by_id")
    async def get_by_id(self, user_id: UUID) -> UserResponse:
        """Возвращает пользователя по идентификатору."""
        user_cache_key = get_user_cache_key(user_id)

        user = await self._cache.get_model(
            key=user_cache_key,
            model_type=UserResponse,
        )
        if user is not None:
            return user

        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            user = UserResponse.model_validate(user_model)

        await self._cache.set_model(
            key=user_cache_key,
            value=user,
            ttl=self._user_cache_ttl,
        )

        return user

    @trace_method("users.update_profile")
    async def update_profile(
        self,
        user_id: UUID,
        user_data: UserUpdate,
    ) -> UserResponse:
        """Обновляет профиль пользователя."""
        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            fields_set = user_data.model_fields_set

            if "first_name" in fields_set:
                user_model.first_name = user_data.first_name

            if "last_name" in fields_set:
                user_model.last_name = user_data.last_name

            user_model = await uow.users.save(user_model)

            fresh_user_model = await uow.users.get_by_id(
                user_model.id,
            )

            user = UserResponse.model_validate(fresh_user_model)

            await uow.commit()

        await self._cache.delete(
            get_user_cache_key(user_id),
        )

        return user

    @trace_method("users.change_password")
    async def change_password(
        self,
        user_id: UUID,
        password_data: UserPasswordUpdate,
    ) -> None:
        """Меняет пароль пользователя и отзывает refresh-сессии."""
        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            if not verify_password(
                password_data.old_password,
                user_model.password_hash,
            ):
                raise InvalidCredentialsError("Invalid old password")

            user_model.password_hash = hash_password(
                password_data.new_password,
            )

            await uow.users.save(user_model)

            revoked_session_ids = (
                await uow.refresh_sessions.revoke_all_by_user_id(user_id)
            )

            await uow.commit()

        await self._revocation_store.revoke_sessions(
            revoked_session_ids,
        )

        await self._cache.delete(
            get_user_cache_key(user_id),
        )

    @trace_method("users.get_login_history")
    async def get_login_history(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> list[LoginHistoryResponse]:
        """Возвращает историю входов пользователя."""
        created_from = self._normalize_to_utc(created_from)
        created_to = self._normalize_to_utc(created_to)

        if (
            created_from is not None
            and created_to is not None
            and created_from >= created_to
        ):
            raise InvalidLoginHistoryDateRangeError(
                "created_from must be earlier than created_to",
            )

        login_history_cache_key = get_login_history_cache_key(
            user_id=user_id,
            limit=limit,
            offset=offset,
            created_from=created_from,
            created_to=created_to,
        )

        login_history = await self._cache.get_models(
            key=login_history_cache_key,
            model_type=LoginHistoryResponse,
        )
        if login_history is not None:
            return login_history

        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            login_history_models = await uow.login_history.get_by_user_id(
                user_id,
                limit=limit,
                offset=offset,
                created_from=created_from,
                created_to=created_to,
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

    @trace_method("users.assign_role")
    async def assign_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> UserResponse:
        """Назначает роль пользователю."""
        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            role_model = await uow.roles.get_by_id(role_id)
            if role_model is None:
                raise RoleNotFoundError("Role not found")

            user_model = await uow.users.add_role(
                user_model,
                role_model,
            )

            await uow.commit()

            user = UserResponse.model_validate(user_model)

        await self._cache.delete(
            get_user_cache_key(user_id),
        )

        return user

    @trace_method("users.remove_role")
    async def remove_role(
        self,
        user_id: UUID,
        role_id: UUID,
    ) -> UserResponse:
        """Удаляет роль у пользователя."""
        async with self._uow_factory() as uow:
            user_model = await uow.users.get_by_id(user_id)
            if user_model is None:
                raise UserNotFoundError("User not found")

            role_model = await uow.roles.get_by_id(role_id)
            if role_model is None:
                raise RoleNotFoundError("Role not found")

            user_model = await uow.users.remove_role(
                user_model,
                role_model,
            )

            await uow.commit()

            user = UserResponse.model_validate(user_model)

        await self._cache.delete(
            get_user_cache_key(user_id),
        )

        return user

    @staticmethod
    def _normalize_to_utc(
        value: datetime | None,
    ) -> datetime | None:
        """Нормализует datetime в UTC."""
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)
