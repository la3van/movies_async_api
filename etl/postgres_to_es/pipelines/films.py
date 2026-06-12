"""Пайплайн загрузки фильмов в Elasticsearch."""
import logging
from typing import Any

from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.state import StateData
from postgres_to_es.transforms import transform_films

logger = logging.getLogger(__name__)


class FilmsPipeline(BasePipeline):
    """Пайплайн загрузки индекса фильмов."""
    def prepare(self) -> None:
        """Создает индекс фильмов, если его еще нет."""
        self.elasticsearch.create_index_if_not_exists(
            index_name=self.settings.movies_index,
            schema_filename='movies_schema.json',
        )

    def run_iteration(self, connection: Any) -> bool:
        """Выполняет одну итерацию загрузки фильмов."""
        film_work_changes = self.postgres.get_changed_film_work_ids(
            connection=connection,
            last_modified=self._get_state('film_work_modified'),
            last_id=self._get_state('film_work_id'),
            limit=self.settings.batch_size,
        )

        person_changes = self.postgres.get_changed_person_ids(
            connection=connection,
            last_modified=self._get_state('person_modified'),
            last_id=self._get_state('person_id'),
            limit=self.settings.batch_size,
        )

        genre_changes = self.postgres.get_changed_genre_ids(
            connection=connection,
            last_modified=self._get_state('genre_modified'),
            last_id=self._get_state('genre_id'),
            limit=self.settings.batch_size,
        )

        has_changes = bool(
            film_work_changes or person_changes or genre_changes,
        )

        if not has_changes:
            logger.info('Изменения для индекса фильмов не найдены.')
            return False

        film_work_ids = {record.id for record in film_work_changes}

        if person_changes:
            person_ids = [record.id for record in person_changes]
            film_work_ids.update(
                self.postgres.get_film_work_ids_by_person_ids(
                    connection=connection,
                    person_ids=person_ids,
                ),
            )

        if genre_changes:
            genre_ids = [record.id for record in genre_changes]
            film_work_ids.update(
                self.postgres.get_film_work_ids_by_genre_ids(
                    connection=connection,
                    genre_ids=genre_ids,
                ),
            )

        if film_work_ids:
            postgres_films = self.postgres.get_films_by_ids(
                connection=connection,
                film_work_ids=list(film_work_ids),
            )
            elastic_movies = transform_films(postgres_films)

            self.elasticsearch.bulk_load(
                index_name=self.settings.movies_index,
                documents=elastic_movies,
            )

        state_updates: StateData = {}
        state_updates.update(
            self._get_cursor_update('film_work', film_work_changes),
        )
        state_updates.update(
            self._get_cursor_update('person', person_changes),
        )
        state_updates.update(
            self._get_cursor_update('genre', genre_changes),
        )

        if state_updates:
            self.state.set_states(state_updates)

        logger.info('Итерация пайплайна фильмов завершена.')
        return True
