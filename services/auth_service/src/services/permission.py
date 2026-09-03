"""Сервис работы с правами доступа."""

from uuid import UUID

from api.v1.schemas.permissions import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)
from cache.base import Cache
from core.tracing import trace_method
from services.cache_keys.permissions import (
    get_permission_cache_key,
    get_permissions_cache_key,
    get_permissions_cache_pattern,
)
from services.cache_keys.roles import (
    get_role_cache_pattern,
    get_roles_cache_pattern,
)
from services.cache_keys.users import get_users_cache_pattern
from services.exceptions import (
    PermissionAlreadyExistsError,
    PermissionNotFoundError,
)
from unit_of_work.base import UnitOfWorkFactory


class PermissionService:
    """Сервис управления правами доступа."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        cache: Cache,
        permission_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис прав доступа."""
        self._uow_factory = uow_factory
        self._cache = cache
        self._permission_cache_ttl = permission_cache_ttl

    @trace_method("permissions.get_by_id")
    async def get_by_id(
        self,
        permission_id: UUID,
    ) -> PermissionResponse:
        """Возвращает право доступа по идентификатору."""
        permission_cache_key = get_permission_cache_key(permission_id)

        permission = await self._cache.get_model(
            key=permission_cache_key,
            model_type=PermissionResponse,
        )
        if permission is not None:
            return permission

        async with self._uow_factory() as uow:
            permission_model = await uow.permissions.get_by_id(
                permission_id,
            )
            if permission_model is None:
                raise PermissionNotFoundError("Permission not found")

            permission = PermissionResponse.model_validate(
                permission_model,
            )

        await self._cache.set_model(
            key=permission_cache_key,
            value=permission,
            ttl=self._permission_cache_ttl,
        )

        return permission

    @trace_method("permissions.get_all")
    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PermissionResponse]:
        """Возвращает список прав доступа."""
        cache_key = get_permissions_cache_key(limit, offset)

        permissions = await self._cache.get_models(
            key=cache_key,
            model_type=PermissionResponse,
        )
        if permissions is not None:
            return permissions

        async with self._uow_factory() as uow:
            permission_models = await uow.permissions.get_all(
                limit=limit,
                offset=offset,
            )

            permissions = [
                PermissionResponse.model_validate(permission)
                for permission in permission_models
            ]

        await self._cache.set_models(
            key=cache_key,
            values=permissions,
            ttl=self._permission_cache_ttl,
        )

        return permissions

    @trace_method("permissions.create")
    async def create(
        self,
        permission_data: PermissionCreate,
    ) -> PermissionResponse:
        """Создаёт право доступа."""
        async with self._uow_factory() as uow:
            existing_permission = await uow.permissions.get_by_code(
                permission_data.code,
            )
            if existing_permission is not None:
                raise PermissionAlreadyExistsError(
                    "Permission already exists",
                )

            permission_model = await uow.permissions.create(
                code=permission_data.code,
                description=permission_data.description,
            )

            await uow.commit()

            fresh_permission_model = await uow.permissions.get_by_id(
                permission_model.id,
            )

            permission = PermissionResponse.model_validate(
                fresh_permission_model,
            )

        await self._invalidate_permission_collection_cache()

        return permission

    @trace_method("permissions.update")
    async def update(
        self,
        permission_id: UUID,
        permission_data: PermissionUpdate,
    ) -> PermissionResponse:
        """Обновляет право доступа."""
        async with self._uow_factory() as uow:
            permission_model = await uow.permissions.get_by_id(
                permission_id,
            )
            if permission_model is None:
                raise PermissionNotFoundError("Permission not found")

            fields_set = permission_data.model_fields_set

            if (
                "code" in fields_set
                and permission_data.code is not None
                and permission_data.code != permission_model.code
            ):
                existing_permission = await uow.permissions.get_by_code(
                    permission_data.code,
                )
                if existing_permission is not None:
                    raise PermissionAlreadyExistsError(
                        "Permission already exists",
                    )

                permission_model.code = permission_data.code

            if "description" in fields_set:
                permission_model.description = permission_data.description

            permission_model = await uow.permissions.save(
                permission_model,
            )

            await uow.commit()

            fresh_permission_model = await uow.permissions.get_by_id(
                permission_model.id,
            )

            permission = PermissionResponse.model_validate(
                fresh_permission_model,
            )

        await self._invalidate_permission_cache(permission_id)

        return permission

    async def _invalidate_permission_collection_cache(self) -> None:
        """Инвалидирует кеш списков прав доступа."""
        await self._cache.delete_by_pattern(
            get_permissions_cache_pattern(),
        )

    async def _invalidate_permission_cache(
        self,
        permission_id: UUID,
    ) -> None:
        """Инвалидирует кеши, зависящие от права доступа."""
        await self._cache.delete(
            get_permission_cache_key(permission_id),
        )
        await self._invalidate_permission_collection_cache()

        await self._cache.delete_by_pattern(
            get_role_cache_pattern(),
        )
        await self._cache.delete_by_pattern(
            get_roles_cache_pattern(),
        )
        await self._cache.delete_by_pattern(
            get_users_cache_pattern(),
        )
