"""Модуль бизнес-логики для работы с персонами."""
from core.tracing import trace_method
from cache.base import Cache
from models.person import Person
from models.film import ShortFilm
from repositories.interfaces.person import PersonRepository
from services.cache_keys.persons import (
    get_person_cache_key,
    get_persons_cache_key,
    get_person_films_cache_key,
)


class PersonService:
    """Сервис для получения информации о персонах.

    Сервис управляет бизнес-сценариями получения персон и связанных с ними
    сущностей:
    проверяет кеш, обращается к основному хранилищу через репозиторий
    и сохраняет полученные результаты в кеш.
    """
    def __init__(
        self,
        repository: PersonRepository,
        cache: Cache,
        cache_ttl: int,
    ) -> None:
        """Инициализирует сервис персон."""
        self._repository = repository
        self._cache = cache
        self._cache_ttl = cache_ttl

    @trace_method("content.persons.get_by_id")
    async def get_person_by_id(
        self,
        person_id: str
    ) -> Person | None:
        """Возвращает персону по id или None, если персона не найдена."""
        person_cache_key = get_person_cache_key(person_id)

        person = await self._cache.get_model(
            key=person_cache_key,
            model_type=Person,
        )
        if person is not None:
            return person

        person = await self._repository.get_by_id(person_id)
        if person is None:
            return None

        await self._cache.set_model(
            key=person_cache_key,
            value=person,
            ttl=self._cache_ttl,
        )

        return person

    @trace_method("content.persons.get_many")
    async def get_persons(
        self,
        query: str | None = None,
        sort: str | None = None,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[Person]:
        """Возвращает список персон с учётом поиска, сортировки и пагинации."""
        normalized_query = query.strip() if query else None
        if not normalized_query:
            normalized_query = None

        effective_sort = sort
        if effective_sort is None and normalized_query is None:
            effective_sort = 'full_name'

        persons_cache_key = get_persons_cache_key(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )

        persons = await self._cache.get_models(
            key=persons_cache_key,
            model_type=Person,
        )
        if persons is not None:
            return persons

        persons = await self._repository.get_many(
            query=normalized_query,
            sort=effective_sort,
            page_number=page_number,
            page_size=page_size,
        )
        await self._cache.set_models(
            key=persons_cache_key,
            values=persons,
            ttl=self._cache_ttl,
        )

        return persons

    @trace_method("content.persons.get_films")
    async def get_person_films(
        self,
        person_id: str,
        page_number: int = 1,
        page_size: int = 50,
    ) -> list[ShortFilm] | None:
        """Возвращает фильмы, связанные с персоной.
        Если персона не найдена, возвращается None."""
        person = await self.get_person_by_id(person_id)
        if person is None:
            return None

        person_films_cache_key = get_person_films_cache_key(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )

        films = await self._cache.get_models(
            key=person_films_cache_key,
            model_type=ShortFilm,
        )
        if films is not None:
            return films

        films = await self._repository.get_films(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )
        await self._cache.set_models(
            key=person_films_cache_key,
            values=films,
            ttl=self._cache_ttl,
        )

        return films
