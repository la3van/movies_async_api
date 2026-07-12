"""Сервис работы с ролями."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.roles import RoleCreate, RoleResponse, RoleUpdate
from cache.base import Cache
from repositories.interfaces.role import RoleRepository
from services.cache_keys.roles import get_role_cache_key
from services.exceptions import RoleAlreadyExistsError, RoleNotFoundError
from services.permission import PermissionService


class RoleService:
    """Сервис управления ролями."""
    def __init__(
        self,
        session: AsyncSession,
        role_repository: RoleRepository,
        permission_service: PermissionService,
        cache: Cache,
        role_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис ролей."""
        self._session = session
        self._role_repository = role_repository
        self._permission_service = permission_service
        self._cache = cache
        self._role_cache_ttl = role_cache_ttl

    async def get_by_id(self, role_id: UUID) -> RoleResponse:
        """Возвращает роль по идентификатору."""
        role_cache_key = get_role_cache_key(role_id)

        role = await self._cache.get_model(
            key=role_cache_key,
            model_type=RoleResponse,
        )
        if role is not None:
            return role

        role_model = await self._role_repository.get_by_id(role_id)
        if role_model is None:
            raise RoleNotFoundError('Role not found')

        role = RoleResponse.model_validate(role_model)

        await self._cache.set_model(
            key=role_cache_key,
            value=role,
            ttl=self._role_cache_ttl,
        )

        return role

    async def get_all(
        self,
        limit: int,
        offset: int,
    ) -> list[RoleResponse]:
        """Возвращает список ролей."""
        role_models = await self._role_repository.get_all(
            limit=limit,
            offset=offset,
        )

        return [
            RoleResponse.model_validate(role_model)
            for role_model in role_models
        ]

    async def get_models_by_ids(self, role_ids: list[UUID]):
        """Возвращает ORM-модели ролей по списку идентификаторов."""
        roles = await self._role_repository.get_by_ids(role_ids)

        if len(roles) != len(set(role_ids)):
            raise RoleNotFoundError('Some roles were not found')

        return roles

    async def create(self, role_data: RoleCreate) -> RoleResponse:
        """Создаёт роль."""
        existing_role = await self._role_repository.get_by_name(role_data.name)
        if existing_role is not None:
            raise RoleAlreadyExistsError('Role already exists')

        permissions = await self._permission_service.get_models_by_ids(
            role_data.permission_ids,
        )

        try:
            role_model = await self._role_repository.create(
                name=role_data.name,
                description=role_data.description,
                is_default=role_data.is_default,
                permissions=permissions,
            )

            await self._session.commit()

            fresh_role_model = await self._role_repository.get_by_id(
                role_model.id
            )

            role = RoleResponse.model_validate(fresh_role_model)

            await self._cache.set_model(
                key=get_role_cache_key(role_model.id),
                value=role,
                ttl=self._role_cache_ttl,
            )

            return role

        except Exception:
            await self._session.rollback()
            raise

    async def update(
        self,
        role_id: UUID,
        role_data: RoleUpdate,
    ) -> RoleResponse:
        """Обновляет роль."""
        role_model = await self._role_repository.get_by_id(role_id)
        if role_model is None:
            raise RoleNotFoundError('Role not found')

        fields_set = role_data.model_fields_set

        if 'name' in fields_set and role_data.name != role_model.name:
            existing_role = await self._role_repository.get_by_name(
                role_data.name,
            )
            if existing_role is not None:
                raise RoleAlreadyExistsError('Role already exists')

            role_model.name = role_data.name

        if 'description' in fields_set:
            role_model.description = role_data.description

        if 'is_default' in fields_set:
            role_model.is_default = role_data.is_default

        if 'permission_ids' in fields_set:
            permissions = await self._permission_service.get_models_by_ids(
                role_data.permission_ids or [],
            )
            role_model = await self._role_repository.set_permissions(
                role_model,
                permissions,
            )

        try:
            role_model = await self._role_repository.save(role_model)
            await self._session.commit()

            fresh_role_model = await self._role_repository.get_by_id(
                role_model.id
            )

            role = RoleResponse.model_validate(fresh_role_model)

            await self._cache.delete(get_role_cache_key(role_id))
            await self._cache.set_model(
                key=get_role_cache_key(role_id),
                value=role,
                ttl=self._role_cache_ttl,
            )

            return role

        except Exception:
            await self._session.rollback()
            raise

    async def delete(self, role_id: UUID) -> None:
        """Удаляет роль."""
        role_model = await self._role_repository.get_by_id(role_id)
        if role_model is None:
            raise RoleNotFoundError('Role not found')

        try:
            await self._role_repository.delete(role_model)
            await self._session.commit()

            await self._cache.delete(get_role_cache_key(role_id))
        except Exception:
            await self._session.rollback()
            raise
