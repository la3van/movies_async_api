"""Интерфейс репозитория ролей."""
from abc import ABC, abstractmethod
from uuid import UUID

from models.permission import Permission
from models.role import Role


class RoleRepository(ABC):
    """Определяет операции получения и сохранения ролей."""
    @abstractmethod
    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Возвращает роль по идентификатору или None,
        если роль не найдена."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_name(self, name) -> Role | None:
        """Возвращает роль по названию или None,
        если роль не найдена."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_ids(self, role_ids: list[UUID]) -> list[Role]:
        """Возвращает список ролей по списку идентификаторов."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_default_roles(self) -> list[Role]:
        """Возвращает роли, выдаваемые пользователю по умолчанию."""
        pass  # pragma: no cover

    @abstractmethod
    async def create(
        self,
        *,
        name: str,
        description: str | None = None,
        is_default: bool = None,
        permissions: list[Permission] | None = None,
    ) -> Role:
        """Создает роль и возвращает созданную модель."""
        pass  # pragma: no cover

    @abstractmethod
    async def set_permissions(
        self,
        role: Role,
        permissions: list[Permission],
    ) -> Role:
        """Заменяет список permissions у роли."""
        pass  # pragma: no cover
