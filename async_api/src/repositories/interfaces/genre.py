"""Интерфейс репозитория жанров."""
from abc import ABC, abstractmethod

from models.genre import Genre


class GenreRepository(ABC):
    """Определяет операции получения и поиска жанров."""
    @abstractmethod
    async def get_by_id(
        self,
        genre_id: str,
    ) -> Genre | None:
        """Возвращает жанр по идентификатору или None, если жанр не найден."""
        pass  # pragma: no cover

    @abstractmethod
    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Genre]:
        """Возвращает страницу жанров с учётом поиска и сортировки."""
        pass  # pragma: no cover
