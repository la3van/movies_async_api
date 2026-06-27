"""Интерфейсы источников данных для ETL-пайплайнов."""
from abc import ABC, abstractmethod

from psycopg2.extensions import connection as PgConnection


from postgres_to_es.models import (
    ChangedRecord,
    PostgresFilm,
    PostgresGenre,
    PostgresPerson,
)


class FilmsSource(ABC):
    """Источник данных для пайплайна фильмов."""
    @abstractmethod
    def get_changed_film_work_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые фильмы после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_changed_person_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённых персон после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_changed_genre_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые жанры после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_film_work_ids_by_person_ids(
        self,
        connection: PgConnection,
        person_ids: list[str],
    ) -> list[str]:
        """Получает фильмы, связанные с указанными персонами."""
        pass  # pragma: no cover

    @abstractmethod
    def get_film_work_ids_by_genre_ids(
        self,
        connection: PgConnection,
        genre_ids: list[str],
    ) -> list[str]:
        """Получает фильмы, связанные с указанными жанрами."""
        pass  # pragma: no cover

    @abstractmethod
    def get_films_by_ids(
        self,
        connection: PgConnection,
        film_work_ids: list[str],
    ) -> list[PostgresFilm]:
        """Получает полные данные фильмов по идентификаторам."""
        pass  # pragma: no cover


class GenresSource(ABC):
    """Источник данных для пайплайна жанров."""

    @abstractmethod
    def get_changed_genre_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые жанры после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_genres_by_ids(
        self,
        connection: PgConnection,
        genre_ids: list[str],
    ) -> list[PostgresGenre]:
        """Получает полные данные жанров по идентификаторам."""
        pass  # pragma: no cover


class PersonsSource(ABC):
    """Источник данных для пайплайна персон."""

    @abstractmethod
    def get_changed_person_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённых персон после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_changed_film_work_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые фильмы после указанного курсора."""
        pass  # pragma: no cover

    @abstractmethod
    def get_person_ids_by_film_work_ids(
        self,
        connection: PgConnection,
        film_work_ids: list[str],
    ) -> list[str]:
        """Получает персон, связанных с указанными фильмами."""
        pass  # pragma: no cover

    @abstractmethod
    def get_persons_by_ids(
        self,
        connection: PgConnection,
        person_ids: list[str],
    ) -> list[PostgresPerson]:
        """Получает полные данные персон по идентификаторам."""
        pass  # pragma: no cover
