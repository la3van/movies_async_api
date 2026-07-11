"""Интерфейс репозитория пользователей."""
from abc import ABC, abstractmethod
from uuid import UUID

from models.role import Role
from models.user import User


class UserRepository(ABC):
    """Определяет операции получения и сохранения пользователей."""
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Возвращает пользователя по идентификатору или None,
        если пользователь не найден."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_login(self, login: str) -> User | None:
        """Возвращает пользователя по логину или None,
        если пользователь не найден."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None,
        если пользователь не найден."""
        pass  # pragma: no cover

    @abstractmethod
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
        pass  # pragma: no cover

    @abstractmethod
    async def add_roles(self, user: User, roles: list[Role]) -> User:
        """Добавляет пользователю роли и возвращает обновлённую модель."""
        pass  # pragma: no cover

    @abstractmethod
    async def save(self, user: User) -> User:
        """Сохраняет пользователя и возвращает обновлённую модель."""
        pass  # pragma: no cover
