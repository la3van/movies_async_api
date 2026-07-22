"""Сервис работы с ролями."""
from core.tracing import trace_method
from uuid import UUID

from api.v1.schemas.roles import RoleCreate, RoleResponse, RoleUpdate
from cache.base import Cache
from services.cache_keys.roles import (
    get_role_cache_key,
    get_roles_cache_key,
    get_roles_cache_pattern,
)
from services.cache_keys.users import get_users_cache_pattern
from services.exceptions import (
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
)
from unit_of_work.base import UnitOfWorkFactory


class RoleService:
    """Сервис управления ролями."""
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        cache: Cache,
        role_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис ролей."""
        self._uow_factory = uow_factory
        self._cache = cache
        self._role_cache_ttl = role_cache_ttl

    @trace_method("roles.get_by_id")
    async def get_by_id(self, role_id: UUID) -> RoleResponse:
        """Возвращает роль по идентификатору."""
        role_cache_key = get_role_cache_key(role_id)

        role = await self._cache.get_model(
            key=role_cache_key,
            model_type=RoleResponse,
        )
        if role is not None:
            return role

        async with self._uow_factory() as uow:
            role_model = await uow.roles.get_by_id(role_id)
            if role_model is None:
                raise RoleNotFoundError('Role not found')

            role = RoleResponse.model_validate(role_model)

        await self._cache.set_model(
            key=role_cache_key,
            value=role,
            ttl=self._role_cache_ttl,
        )

        return role

    @trace_method("roles.get_all")
    async def get_all(
        self,
        limit: int,
        offset: int,
    ) -> list[RoleResponse]:
        """Возвращает список ролей."""
        roles_cache_key = get_roles_cache_key(
            limit=limit,
            offset=offset,
        )

        roles = await self._cache.get_models(
            key=roles_cache_key,
            model_type=RoleResponse,
        )
        if roles is not None:
            return roles

        async with self._uow_factory() as uow:
            role_models = await uow.roles.get_all(
                limit=limit,
                offset=offset,
            )

            roles = [
                RoleResponse.model_validate(role_model)
                for role_model in role_models
            ]

        await self._cache.set_models(
            key=roles_cache_key,
            values=roles,
            ttl=self._role_cache_ttl,
        )

        return roles

    @trace_method("roles.create")
    async def create(self, role_data: RoleCreate) -> RoleResponse:
        """Создаёт роль."""
        async with self._uow_factory() as uow:
            existing_role = await uow.roles.get_by_name(role_data.name)
            if existing_role is not None:
                raise RoleAlreadyExistsError('Role already exists')

            permissions = await uow.permissions.get_by_ids(
                role_data.permission_ids,
            )
            if len(permissions) != len(set(role_data.permission_ids)):
                raise PermissionNotFoundError(
                    'Some permissions were not found',
                )

            role_model = await uow.roles.create(
                name=role_data.name,
                description=role_data.description,
                is_default=role_data.is_default,
                permissions=permissions,
            )

            await uow.commit()

            fresh_role_model = await uow.roles.get_by_id(role_model.id)
            if fresh_role_model is None:
                raise RoleNotFoundError('Role not found')

            role = RoleResponse.model_validate(fresh_role_model)

        await self._invalidate_role_collection_cache()

        return role

    @trace_method("roles.update")
    async def update(
        self,
        role_id: UUID,
        role_data: RoleUpdate,
    ) -> RoleResponse:
        """Обновляет роль."""
        async with self._uow_factory() as uow:
            role_model = await uow.roles.get_by_id(role_id)
            if role_model is None:
                raise RoleNotFoundError('Role not found')

            fields_set = role_data.model_fields_set

            if (
                'name' in fields_set
                and role_data.name != role_model.name
            ):
                existing_role = await uow.roles.get_by_name(
                    role_data.name,
                )
                if existing_role is not None:
                    raise RoleAlreadyExistsError(
                        'Role already exists',
                    )

                role_model.name = role_data.name

            if 'description' in fields_set:
                role_model.description = role_data.description

            if 'is_default' in fields_set:
                role_model.is_default = role_data.is_default

            if 'permission_ids' in fields_set:
                permission_ids = role_data.permission_ids or []

                permissions = await uow.permissions.get_by_ids(
                    permission_ids,
                )
                if len(permissions) != len(set(permission_ids)):
                    raise PermissionNotFoundError(
                        'Some permissions were not found',
                    )

                role_model = await uow.roles.set_permissions(
                    role_model,
                    permissions,
                )

            role_model = await uow.roles.save(role_model)

            await uow.commit()

            fresh_role_model = await uow.roles.get_by_id(
                role_model.id,
            )
            if fresh_role_model is None:
                raise RoleNotFoundError('Role not found')

            role = RoleResponse.model_validate(fresh_role_model)

        await self._invalidate_role_cache(role_id)

        return role

    @trace_method("roles.delete")
    async def delete(self, role_id: UUID) -> None:
        """Удаляет роль."""
        async with self._uow_factory() as uow:
            role_model = await uow.roles.get_by_id(role_id)
            if role_model is None:
                raise RoleNotFoundError('Role not found')

            await uow.roles.delete(role_model)
            await uow.commit()

        await self._invalidate_role_cache(role_id)

    async def _invalidate_role_collection_cache(self) -> None:
        """Инвалидирует кеши коллекций ролей."""
        await self._cache.delete_by_pattern(
            get_roles_cache_pattern(),
        )

    async def _invalidate_role_cache(self, role_id: UUID) -> None:
        """Инвалидирует кеши, зависящие от роли."""
        await self._cache.delete(
            get_role_cache_key(role_id),
        )
        await self._invalidate_role_collection_cache()
        await self._cache.delete_by_pattern(
            get_users_cache_pattern(),
        )
