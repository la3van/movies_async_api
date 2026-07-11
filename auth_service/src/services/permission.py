"""Сервис работы с правами доступа."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.schemas.permissions import (
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)
from cache.base import Cache
from repositories.interfaces.permission import PermissionRepository
from services.cache_keys.permissions import get_permission_cache_key
from services.exceptions import (
    PermissionAlreadyExistsError,
    PermissionNotFoundError,
)


class PermissionService:
    """Сервис управления правами доступа."""
    def __init__(
        self,
        session: AsyncSession,
        permission_repository: PermissionRepository,
        cache: Cache,
        permission_cache_ttl: int,
    ) -> None:
        """Инициализирует сервис прав доступа."""
        self._session = session
        self._permission_repository = permission_repository
        self._cache = cache
        self._permission_cache_ttl = permission_cache_ttl

    async def get_by_id(self, permission_id: UUID) -> PermissionResponse:
        """Возвращает право доступа по идентификатору."""
        permission_cache_key = get_permission_cache_key(permission_id)

        permission = await self._cache.get_model(
            key=permission_cache_key,
            model_type=PermissionResponse,
        )
        if permission is not None:
            return permission

        permission_model = await self._permission_repository.get_by_id(
            permission_id,
        )
        if permission_model is None:
            raise PermissionNotFoundError('Permission not found')

        permission = PermissionResponse.model_validate(permission_model)

        await self._cache.set_model(
            key=permission_cache_key,
            value=permission,
            ttl=self._permission_cache_ttl,
        )

        return permission

    async def get_models_by_ids(self, permission_ids: list[UUID]):
        """Возвращает ORM-модели прав доступа по списку идентификаторов."""
        permissions = await self._permission_repository.get_by_ids(
            permission_ids,
        )

        if len(permissions) != len(set(permission_ids)):
            raise PermissionNotFoundError('Some permissions were not found')

        return permissions

    async def create(
        self,
        permission_data: PermissionCreate,
    ) -> PermissionResponse:
        """Создаёт право доступа."""
        existing_permission = await self._permission_repository.get_by_code(
            permission_data.code,
        )
        if existing_permission is not None:
            raise PermissionAlreadyExistsError('Permission already exists')

        try:
            permission_model = await self._permission_repository.create(
                code=permission_data.code,
                description=permission_data.description,
            )

            await self._session.commit()

            permission = PermissionResponse.model_validate(permission_model)

            await self._cache.set_model(
                key=get_permission_cache_key(permission_model.id),
                value=permission,
                ttl=self._permission_cache_ttl,
            )

            return permission
        except Exception:
            await self._session.rollback()
            raise

    async def update(
        self,
        permission_id: UUID,
        permission_data: PermissionUpdate,
    ) -> PermissionResponse:
        """Обновляет право доступа."""
        permission_model = await self._permission_repository.get_by_id(
            permission_id,
        )
        if permission_model is None:
            raise PermissionNotFoundError('Permission not found')

        fields_set = permission_data.model_fields_set

        if (
            'code' in fields_set and
            permission_data.code != permission_model.code
        ):
            existing_permission = (
                await self._permission_repository.get_by_code(
                    permission_data.code,
                )
            )
            if existing_permission is not None:
                raise PermissionAlreadyExistsError('Permission already exists')

            permission_model.code = permission_data.code

        if 'description' in fields_set:
            permission_model.description = permission_data.description

        try:
            permission_model = await self._permission_repository.save(
                permission_model,
            )
            await self._session.commit()

            permission = PermissionResponse.model_validate(permission_model)

            await self._cache.delete(get_permission_cache_key(permission_id))
            await self._cache.set_model(
                key=get_permission_cache_key(permission_id),
                value=permission,
                ttl=self._permission_cache_ttl,
            )

            return permission
        except Exception:
            await self._session.rollback()
            raise
