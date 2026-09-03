"""Пайплайн загрузки фильмов в целевой индекс."""

import logging

from psycopg2.extensions import connection as PgConnection

from postgres_to_es.interfaces import DocumentLoader, FilmsSource
from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.state import State, StateData
from postgres_to_es.transforms import transform_films

logger = logging.getLogger(__name__)

MOVIES_SCHEMA_FILENAME = "movies.json"


class FilmsPipeline(BasePipeline):
    """Загружает документы фильмов."""

    def __init__(
        self,
        source: FilmsSource,
        loader: DocumentLoader,
        state: State,
        index_name: str,
        batch_size: int,
    ) -> None:
        """Инициализирует пайплайн фильмов."""
        super().__init__(
            loader=loader,
            state=state,
            index_name=index_name,
            schema_filename=MOVIES_SCHEMA_FILENAME,
            batch_size=batch_size,
        )

        self._source = source

    def run_iteration(
        self,
        connection: PgConnection,
    ) -> bool:
        """Выполняет одну итерацию загрузки фильмов."""
        film_modified, film_id = self._get_cursor(
            "film_work",
        )
        person_modified, person_id = self._get_cursor(
            "person",
        )
        genre_modified, genre_id = self._get_cursor(
            "genre",
        )

        film_work_changes = self._source.get_changed_film_work_ids(
            connection=connection,
            last_modified=film_modified,
            last_id=film_id,
            limit=self._batch_size,
        )

        person_changes = self._source.get_changed_person_ids(
            connection=connection,
            last_modified=person_modified,
            last_id=person_id,
            limit=self._batch_size,
        )

        genre_changes = self._source.get_changed_genre_ids(
            connection=connection,
            last_modified=genre_modified,
            last_id=genre_id,
            limit=self._batch_size,
        )

        if not (film_work_changes or person_changes or genre_changes):
            logger.info(
                "Изменения для индекса фильмов не найдены.",
            )
            return False

        film_work_ids = {record.id for record in film_work_changes}

        if person_changes:
            changed_person_ids = [record.id for record in person_changes]

            related_film_ids = self._source.get_film_work_ids_by_person_ids(
                connection=connection,
                person_ids=changed_person_ids,
            )

            film_work_ids.update(related_film_ids)

        if genre_changes:
            changed_genre_ids = [record.id for record in genre_changes]

            related_film_ids = self._source.get_film_work_ids_by_genre_ids(
                connection=connection,
                genre_ids=changed_genre_ids,
            )

            film_work_ids.update(related_film_ids)

        if film_work_ids:
            postgres_films = self._source.get_films_by_ids(
                connection=connection,
                film_work_ids=sorted(film_work_ids),
            )

            movie_documents = transform_films(
                postgres_films,
            )

            self._loader.bulk_load(
                index_name=self._index_name,
                documents=movie_documents,
            )

        state_updates: StateData = {}

        state_updates.update(
            self._get_cursor_update(
                prefix="film_work",
                records=film_work_changes,
            ),
        )
        state_updates.update(
            self._get_cursor_update(
                prefix="person",
                records=person_changes,
            ),
        )
        state_updates.update(
            self._get_cursor_update(
                prefix="genre",
                records=genre_changes,
            ),
        )

        self._state.set_states(state_updates)

        logger.info(
            "Итерация пайплайна фильмов завершена.",
        )

        return True
