"""Интерфейс репозитория закладок."""

from abc import ABC, abstractmethod
from uuid import UUID

from models.bookmark import Bookmark


class BookmarkRepository(ABC):
    """Операции хранения пользовательских закладок."""

    @abstractmethod
    async def upsert(self, user_id: UUID, film_id: UUID) -> Bookmark:
        """Идемпотентно добавить фильм в закладки."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, user_id: UUID, film_id: UUID) -> Bookmark | None:
        """Вернуть одну закладку."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self, user_id: UUID, page_number: int, page_size: int
    ) -> list[Bookmark]:
        """Вернуть страницу закладок в порядке добавления."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, user_id: UUID, film_id: UUID) -> bool:
        """Удалить закладку и вернуть признак существования."""
        raise NotImplementedError
