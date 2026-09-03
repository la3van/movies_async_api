"""PostgreSQL-репозитории пользователей."""

from uuid import UUID

from models.role import Role
from models.user import User
from repositories.interfaces.user import UserRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class PostgresUserRepository(UserRepository):
    """Реализует операции с пользователями в PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет сессию PostgreSQL."""
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Возвращает пользователя по идентификатору или None,
        если пользователь не найден."""
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_login(self, login: str) -> User | None:
        """Возвращает пользователя по логину или None,
        если пользователь не найден."""
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.login == login)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None,
        если пользователь не найден."""
        statement = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        login: str,
        email: str,
        password_hash: str,
        first_name: str | None = None,
        last_name: str | None = None,
        is_active: bool = True,
        is_superuser: bool = False,
    ) -> User:
        """Создаёт пользователя и возвращает созданную модель."""
        user = User(
            login=login,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_superuser=is_superuser,
            roles=[],
        )

        self.session.add(user)
        await self.session.flush()
        return user

    async def add_roles(self, user: User, roles: list[Role]) -> User:
        """Добавляет пользователю роли и возвращает обновлённую модель."""

        existing_role_ids = {role.id for role in user.roles}

        for role in roles:
            if role.id not in existing_role_ids:
                user.roles.append(role)

        self.session.add(user)
        await self.session.flush()

        return user

    async def add_role(self, user: User, role: Role) -> User:
        """Добавляет пользователю роль и возвращает обновлённую модель."""
        existing_role_ids = {existing_role.id for existing_role in user.roles}

        if role.id not in existing_role_ids:
            user.roles.append(role)

        self.session.add(user)
        await self.session.flush()

        return user

    async def remove_role(self, user: User, role: Role) -> User:
        """Добавляет пользователю роль и возвращает обновлённую модель."""
        user.roles = [
            existing_role
            for existing_role in user.roles
            if existing_role.id != role.id
        ]

        self.session.add(user)
        await self.session.flush()

        return user

    async def save(self, user: User) -> User:
        """Сохраняет пользователя и возвращает обновлённую модель."""
        self.session.add(user)
        await self.session.flush()

        return user
