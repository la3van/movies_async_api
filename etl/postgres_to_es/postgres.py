"""Модуль для чтения данных из PostgreSQL."""

import json
import logging
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg2
from psycopg2 import InterfaceError, OperationalError
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import RealDictCursor

from postgres_to_es.backoff import backoff
from postgres_to_es.config import get_settings
from postgres_to_es.models import (
    ChangedRecord,
    PostgresFilmGenre,
    PostgresFilmPerson,
    PostgresGenre,
    PostgresFilm,
    PostgresPerson,
    PostgresPersonFilm,
)


logger = logging.getLogger(__name__)

ALLOWED_TABLES = {
    'film_work',
    'person',
    'genre',
}


class PostgresExtractor:
    """Класс для извлечения данных из PostgreSQL."""

    def __init__(self) -> None:
        """Инициализирует параметры подключения к PostgreSQL."""
        self.settings = get_settings()
        self.connection_params: dict[str, Any] = {
            'dbname': self.settings.postgres_db,
            'user': self.settings.postgres_user,
            'password': self.settings.postgres_password,
            'host': self.settings.postgres_host,
            'port': self.settings.postgres_port,
            'connect_timeout': self.settings.postgres_connect_timeout,
            'options': self._build_options(),
        }

    def _build_options(self) -> str:
        """Формирует дополнительные параметры подключения к PostgreSQL."""
        options: list[str] = []

        if self.settings.postgres_options:
            options.append(self.settings.postgres_options)

        options.append(
            '-c statement_timeout='
            f'{self.settings.postgres_statement_timeout_ms}',
        )

        return ' '.join(options)

    @backoff(exceptions=(InterfaceError, OperationalError))
    def _connect(self) -> PgConnection:
        """Создаёт подключение к PostgreSQL."""
        pg_connection = psycopg2.connect(**self.connection_params)
        pg_connection.autocommit = True
        return pg_connection

    @contextmanager
    def connection(self) -> Iterator[PgConnection]:
        """Создаёт подключение к PostgreSQL на одну итерацию ETL."""
        pg_connection = self._connect()

        try:
            yield pg_connection
        except Exception:
            logger.exception('Ошибка при работе с PostgreSQL.')
            raise
        finally:
            pg_connection.close()

    @backoff(exceptions=(OperationalError, InterfaceError))
    def _fetch_all(
        self,
        connection: PgConnection,
        query: str,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Выполняет SQL-запрос и возвращает все строки."""
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def _get_changed_records(
        self,
        connection: PgConnection,
        table_name: str,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые записи из указанной таблицы."""
        if table_name not in ALLOWED_TABLES:
            raise ValueError(f'Неподдерживаемая таблица: {table_name}')

        modified_expression = (
            "COALESCE(modified, created, '0001-01-01'::timestamp)"
        )

        query = f"""
            SELECT
                id,
                {modified_expression} AS modified
            FROM content.{table_name}
            WHERE ({modified_expression}, id) > (
                %(last_modified)s::timestamp,
                %(last_id)s::uuid
            )
            ORDER BY {modified_expression}, id
            LIMIT %(limit)s;
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={
                'last_modified': last_modified,
                'last_id': last_id,
                'limit': limit,
            },
        )

        return [
            ChangedRecord(
                id=str(row['id']),
                modified=row['modified'],
            )
            for row in rows
        ]

    def get_changed_film_work_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые записи из таблицы film_work."""
        return self._get_changed_records(
            connection=connection,
            table_name='film_work',
            last_modified=last_modified,
            last_id=last_id,
            limit=limit,
        )

    def get_changed_person_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые записи из таблицы person."""
        return self._get_changed_records(
            connection=connection,
            table_name='person',
            last_modified=last_modified,
            last_id=last_id,
            limit=limit,
        )

    def get_changed_genre_ids(
        self,
        connection: PgConnection,
        last_modified: str,
        last_id: str,
        limit: int,
    ) -> list[ChangedRecord]:
        """Получает изменённые записи из таблицы genre."""
        return self._get_changed_records(
            connection=connection,
            table_name='genre',
            last_modified=last_modified,
            last_id=last_id,
            limit=limit,
        )

    def get_film_work_ids_by_person_ids(
        self,
        connection: PgConnection,
        person_ids: list[str],
    ) -> list[str]:
        """Получает id фильмов, связанных с изменёнными персонами."""
        if not person_ids:
            return []

        query = """
            SELECT DISTINCT film_work_id
            FROM content.person_film_work
            WHERE person_id = ANY(%(person_ids)s::uuid[]);
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'person_ids': person_ids},
        )

        return [str(row['film_work_id']) for row in rows]

    def get_film_work_ids_by_genre_ids(
        self,
        connection: PgConnection,
        genre_ids: list[str],
    ) -> list[str]:
        """Получает id фильмов, связанных с изменёнными жанрами."""
        if not genre_ids:
            return []

        query = """
            SELECT DISTINCT film_work_id
            FROM content.genre_film_work
            WHERE genre_id = ANY(%(genre_ids)s::uuid[]);
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'genre_ids': genre_ids},
        )

        return [str(row['film_work_id']) for row in rows]

    def get_person_ids_by_film_work_ids(
        self,
        connection: PgConnection,
        film_work_ids: list[str],
    ) -> list[str]:
        """Получает id персон, связанных с изменёнными фильмами."""
        if not film_work_ids:
            return []

        query = """
            SELECT DISTINCT person_id
            FROM content.person_film_work
            WHERE film_work_id = ANY(%(film_work_ids)s::uuid[]);
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'film_work_ids': film_work_ids},
        )

        return [str(row['person_id']) for row in rows]

    def get_films_by_ids(
        self,
        connection: PgConnection,
        film_work_ids: list[str],
    ) -> list[PostgresFilm]:
        """Получает полные данные фильмов по их id."""
        if not film_work_ids:
            return []

        query = """
            WITH selected_film_work AS (
                SELECT
                    id,
                    title,
                    description,
                    rating
                FROM content.film_work
                WHERE id = ANY(%(film_work_ids)s::uuid[])
            ),
            genres AS (
                SELECT
                    gfw.film_work_id,
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'uuid', g.id::text,
                            'name', g.name
                        )
                    ) AS genre
                FROM content.genre_film_work gfw
                JOIN content.genre g ON g.id = gfw.genre_id
                WHERE gfw.film_work_id = ANY(%(film_work_ids)s::uuid[])
                GROUP BY gfw.film_work_id
            ),
            persons AS (
                SELECT
                    pfw.film_work_id,
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'uuid', p.id::text,
                            'full_name', p.full_name
                        )
                    ) FILTER (
                        WHERE pfw.role = 'actor'
                    ) AS actors,
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'uuid', p.id::text,
                            'full_name', p.full_name
                        )
                    ) FILTER (
                        WHERE pfw.role = 'writer'
                    ) AS writers,
                    JSONB_AGG(
                        DISTINCT JSONB_BUILD_OBJECT(
                            'uuid', p.id::text,
                            'full_name', p.full_name
                        )
                    ) FILTER (
                        WHERE pfw.role = 'director'
                    ) AS directors
                FROM content.person_film_work pfw
                JOIN content.person p ON p.id = pfw.person_id
                WHERE pfw.film_work_id = ANY(%(film_work_ids)s::uuid[])
                GROUP BY pfw.film_work_id
            )
            SELECT
                fw.id,
                fw.title,
                fw.description,
                fw.rating,
                COALESCE(g.genre, '[]'::jsonb) AS genre,
                COALESCE(p.actors, '[]'::jsonb) AS actors,
                COALESCE(p.writers, '[]'::jsonb) AS writers,
                COALESCE(p.directors, '[]'::jsonb) AS directors
            FROM selected_film_work fw
            LEFT JOIN genres g ON g.film_work_id = fw.id
            LEFT JOIN persons p ON p.film_work_id = fw.id
            ORDER BY fw.id;
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'film_work_ids': film_work_ids},
        )

        return [self._row_to_film(row) for row in rows]

    def get_genres_by_ids(
        self,
        connection: PgConnection,
        genre_ids: list[str],
    ) -> list[PostgresGenre]:
        """Получает полные данные жанров по их id."""
        if not genre_ids:
            return []

        query = """
            SELECT
                id,
                name,
                description
            FROM content.genre
            WHERE id = ANY(%(genre_ids)s::uuid[])
            ORDER BY name, id;
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'genre_ids': genre_ids},
        )

        return [self._row_to_genre(row) for row in rows]

    def get_persons_by_ids(
        self,
        connection: PgConnection,
        person_ids: list[str],
    ) -> list[PostgresPerson]:
        """Получает полные данные персон по их id."""
        if not person_ids:
            return []

        query = """
            WITH selected_person AS (
                SELECT
                    id,
                    full_name
                FROM content.person
                WHERE id = ANY(%(person_ids)s::uuid[])
            ),
            person_film_roles AS (
                SELECT
                    pfw.person_id,
                    pfw.film_work_id,
                    ARRAY_AGG(DISTINCT pfw.role ORDER BY pfw.role) AS roles
                FROM content.person_film_work pfw
                WHERE pfw.person_id = ANY(%(person_ids)s::uuid[])
                GROUP BY pfw.person_id, pfw.film_work_id
            ),
            person_films AS (
                SELECT
                    pfr.person_id,
                    JSONB_AGG(
                        JSONB_BUILD_OBJECT(
                            'uuid', pfr.film_work_id::text,
                            'roles', pfr.roles
                        )
                        ORDER BY pfr.film_work_id
                    ) AS films
                FROM person_film_roles pfr
                GROUP BY pfr.person_id
            )
            SELECT
                p.id,
                p.full_name,
                COALESCE(pf.films, '[]'::jsonb) AS films
            FROM selected_person p
            LEFT JOIN person_films pf ON pf.person_id = p.id
            ORDER BY p.full_name, p.id;
        """

        rows = self._fetch_all(
            connection=connection,
            query=query,
            params={'person_ids': person_ids},
        )

        return [self._row_to_person(row) for row in rows]

    def _row_to_film(self, row: dict[str, Any]) -> PostgresFilm:
        """Преобразует строку PostgreSQL в модель фильма."""
        rating = row['rating']

        return PostgresFilm(
            uuid=str(row['id']),
            title=row['title'],
            description=row['description'],
            imdb_rating=float(rating) if rating is not None else None,
            genre=self._parse_film_genres(row['genre']),
            actors=self._parse_film_persons(row['actors']),
            writers=self._parse_film_persons(row['writers']),
            directors=self._parse_film_persons(row['directors']),
        )

    def _row_to_genre(self, row: dict[str, Any]) -> PostgresGenre:
        """Преобразует строку PostgreSQL в модель жанра."""
        return PostgresGenre(
            uuid=str(row['id']),
            name=row['name'],
            description=row['description'],
        )

    def _row_to_person(self, row: dict[str, Any]) -> PostgresPerson:
        """Преобразует строку PostgreSQL в модель персоны."""
        return PostgresPerson(
            uuid=str(row['id']),
            full_name=row['full_name'],
            films=self._parse_person_films(row['films']),
        )

    def _parse_film_genres(self, value: Any) -> list[PostgresFilmGenre]:
        """Преобразует JSON со списком жанров фильма в модели."""
        return [
            PostgresFilmGenre(
                uuid=str(genre['uuid']),
                name=genre['name'],
            )
            for genre in self._parse_json_list(value)
        ]

    def _parse_film_persons(self, value: Any) -> list[PostgresFilmPerson]:
        """Преобразует JSON со списком персон фильма в модели."""
        return [
            PostgresFilmPerson(
                uuid=str(person['uuid']),
                full_name=person['full_name'],
            )
            for person in self._parse_json_list(value)
        ]

    def _parse_person_films(self, value: Any) -> list[PostgresPersonFilm]:
        """Преобразует JSON со списком фильмов персоны в модели."""
        return [
            PostgresPersonFilm(
                uuid=str(film['uuid']),
                roles=list(film['roles'] or []),
            )
            for film in self._parse_json_list(value)
        ]

    @staticmethod
    def _parse_json_list(value: Any) -> list[dict[str, Any]]:
        """Преобразует JSONB-значение PostgreSQL в список словарей."""
        if value is None:
            return []

        if isinstance(value, str):
            value = json.loads(value)

        if isinstance(value, list):
            return value

        raise ValueError('Ожидался JSON-список из PostgreSQL.')
