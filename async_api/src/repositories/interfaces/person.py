from abc import ABC, abstractmethod

from models.person import Person
from models.film import ShortFilm


class PersonRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self,
        person_id: str,
    ) -> Person | None:
        pass  # pragma: no cover

    @abstractmethod
    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Person]:
        pass  # pragma: no cover

    @abstractmethod
    async def get_films(
        self,
        person_id: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        pass  # pragma: no cover
