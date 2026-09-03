"""Интерфейс репозитория фильмов."""

from abc import ABC, abstractmethod

from models.film import Film, ShortFilm


class FilmRepository(ABC):
    """Определяет операции получения и поиска фильмов."""

    @abstractmethod
    async def get_by_id(self, film_id: str) -> Film | None:
        """Возвращает фильм по идентификатору или None, если фильм
        не найден."""
        # pragma: no cover

    @abstractmethod
    async def get_sorted(
        self,
        sort: str,
        genre_filter: str | None,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает страницу фильмов с сортировкой и фильтром по жанру."""
        # pragma: no cover

    @abstractmethod
    async def search(
        self,
        query: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Ищет фильмы по текстовому запросу с учётом пагинации."""
        # pragma: no cover

    @abstractmethod
    async def find_similar_by_content_and_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает фильмы, похожие по содержимому и жанрам."""
        # pragma: no cover

    @abstractmethod
    async def find_similar_by_genres(
        self,
        film_id: str,
        genre_uuids: list[str],
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает фильмы с общими жанрами."""
        # pragma: no cover
