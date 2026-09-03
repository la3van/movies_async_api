"""Интерфейс репозитория персон."""

from abc import ABC, abstractmethod

from models.film import ShortFilm
from models.person import Person


class PersonRepository(ABC):
    """Определяет операции получения персон и связанных с ними фильмов."""

    @abstractmethod
    async def get_by_id(
        self,
        person_id: str,
    ) -> Person | None:
        """Возвращает персону по идентификатору или None, если она
        не найдена."""
        # pragma: no cover

    @abstractmethod
    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Person]:
        """Возвращает страницу персон с учётом поиска и сортировки."""
        # pragma: no cover

    @abstractmethod
    async def get_films(
        self,
        person_id: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает страницу фильмов, связанных с персоной."""
        # pragma: no cover
