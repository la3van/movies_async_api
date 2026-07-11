"""PostgreSQL-репозиторий ролей."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.permission import Permission
from models.role import Role
from repositories.interfaces.role import RoleRepository


class PostgresRoleRepository(RoleRepository):
    """Реализует операции с ролями в PostgreSQL."""
    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию PostgreSQL."""
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Возвращает роль по идентификатору или None,
        если роль не найдена."""
        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        """Возвращает роль по названию или None,
        если роль не найдена."""
        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.name == name)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        """Возвращает роли по списку идентификаторов."""
        if not role_ids:
            return []

        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id.in_(role_ids))
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_default_roles(self) -> list[Role]:
        """Возвращает роли, выдаваемые пользователю по умолчанию."""
        statement = (
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.is_default.is_(True))
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        permissions: list[Permission] | None = None,
    ) -> Role:
        """Создаёт роль и возвращает созданную модель."""
        role = Role(
            name=name,
            description=description,
            is_default=is_default,
        )

        if permissions:
            role.permissions.extend(permissions)

        self.session.add(role)
        await self.session.flush()

        return role

    async def set_permissions(
        self,
        role: Role,
        permissions: list[Permission],
    ) -> Role:
        """Заменяет список прав доступа у роли."""
        role.permissions = permissions

        self.session.add(role)
        await self.session.flush()

        return role

    async def save(self, role: Role) -> Role:
        """Сохраняет роль и возвращает обновлённую модель."""
        self.session.add(role)
        await self.session.flush()

        return role
