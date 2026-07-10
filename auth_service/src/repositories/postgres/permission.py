"""PostgreSQL-репозиторий прав доступа."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.permission import Permission
from repositories.interfaces.permission import PermissionRepository


class PostgresPermissionRepository(PermissionRepository):
    """Реализует операции с правами доступа в PostgreSQL."""
    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию PostgreSQL."""
        self.session = session

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        """Возвращает право доступа по идентификатору или None,
        если оно не найдено."""
        statement = select(Permission).where(Permission.id == permission_id)

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Permission | None:
        """Возвращает право доступа по коду или None, если оно не найдено."""
        statement = select(Permission).where(Permission.code == code)

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ids(self, permission_ids: list[UUID]) -> list[Permission]:
        """Возвращает права доступа по списку идентификаторов."""
        if not permission_ids:
            return []

        statement = select(Permission).where(Permission.id.in_(permission_ids))
        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def create(
        self,
        *,
        code: str,
        description: str | None = None,
    ) -> Permission:
        """Создаёт право доступа и возвращает созданную модель."""
        permission = Permission(
            code=code,
            description=description,
        )

        self.session.add(permission)
        self.session.flush()

        return permission
