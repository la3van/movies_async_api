"""Интерфейс репозитория прав доступа."""
from abc import ABC, abstractmethod
from uuid import UUID

from models.permission import Permission


class PermissionRepository(ABC):
    """Определяет операции получения и сохранения прав доступа."""
    @abstractmethod
    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        """Возвращает право доступа по идентификатору или None,
        если оно не найдено."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_code(self, code: str) -> Permission | None:
        """Возвращает право доступа по коду или None, если оно не найдено."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Permission]:
        """Возвращает список прав доступа."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_by_ids(self, permission_ids: list[UUID]) -> list[Permission]:
        """Возвращает права доступа по списку идентификаторов."""
        pass  # pragma: no cover

    @abstractmethod
    async def create(
        self,
        *,
        code: str,
        description: str | None = None,
    ) -> Permission:
        """Создаёт право доступа и возвращает созданную модель."""
        pass  # pragma: no cover

    @abstractmethod
    async def save(self, permission: Permission) -> Permission:
        """Сохраняет право доступа и возвращает обновлённую модель."""
        pass  # pragma: no cover
