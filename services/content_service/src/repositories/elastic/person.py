"""Реализация репозитория персон через Elasticsearch."""

from elasticsearch import AsyncElasticsearch, NotFoundError
from models.film import ShortFilm
from models.person import Person
from repositories.elastic.bodies.persons import (
    build_person_films_body,
    build_persons_body,
)
from repositories.elastic.mappers.films import build_short_film
from repositories.interfaces.person import PersonRepository


class ElasticsearchPersonRepository(PersonRepository):
    """Репозиторий персон, использующий Elasticsearch."""

    def __init__(
        self,
        elastic: AsyncElasticsearch,
        persons_index_name: str,
        movies_index_name: str,
        person_sort_fields: dict[str, str],
    ) -> None:
        """Инициализирует репозиторий персон."""
        self._elastic = elastic
        self._persons_index_name = persons_index_name
        self._movies_index_name = movies_index_name
        self._person_sort_fields = person_sort_fields

    async def get_by_id(
        self,
        person_id: str,
    ) -> Person | None:
        """Возвращает персону по идентификатору или None,
        если она не найдена."""
        try:
            document = await self._elastic.get(
                index=self._persons_index_name,
                id=person_id,
            )
        except NotFoundError:
            return None

        return Person.model_validate(document["_source"])

    async def get_many(
        self,
        query: str | None,
        sort: str | None,
        page_number: int,
        page_size: int,
    ) -> list[Person]:
        """Возвращает страницу персон с учётом поиска и сортировки."""
        body = build_persons_body(
            query=query,
            sort=sort,
            page_number=page_number,
            page_size=page_size,
            person_sort_fields=self._person_sort_fields,
        )

        response = await self._elastic.search(
            index=self._persons_index_name,
            body=body,
        )

        return [
            Person.model_validate(hit["_source"])
            for hit in response["hits"]["hits"]
        ]

    async def get_films(
        self,
        person_id: str,
        page_number: int,
        page_size: int,
    ) -> list[ShortFilm]:
        """Возвращает страницу фильмов, связанных с персоной."""
        body = build_person_films_body(
            person_id=person_id,
            page_number=page_number,
            page_size=page_size,
        )

        response = await self._elastic.search(
            index=self._movies_index_name,
            body=body,
        )

        return [
            build_short_film(hit["_source"])
            for hit in response["hits"]["hits"]
        ]
