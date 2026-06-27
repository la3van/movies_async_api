"""Пайплайн загрузки персон в целевой индекс."""
import logging

from psycopg2.extensions import connection as PgConnection

from postgres_to_es.interfaces import (
    DocumentLoader,
    PersonsSource,
)
from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.state import State, StateData
from postgres_to_es.transforms import transform_persons

logger = logging.getLogger(__name__)

PERSONS_SCHEMA_FILENAME = 'persons_schema.json'


class PersonsPipeline(BasePipeline):
    """Загружает документы персон."""
    def __init__(
        self,
        source: PersonsSource,
        loader: DocumentLoader,
        state: State,
        index_name: str,
        batch_size: int,
    ) -> None:
        """Инициализирует пайплайн персон."""
        super().__init__(
            loader=loader,
            state=state,
            index_name=index_name,
            schema_filename=PERSONS_SCHEMA_FILENAME,
            batch_size=batch_size,
        )

        self._source = source

    def run_iteration(
        self,
        connection: PgConnection,
    ) -> bool:
        """Выполняет одну итерацию загрузки персон."""
        person_modified, person_id = self._get_cursor(
            'person',
        )
        film_modified, film_id = self._get_cursor(
            'film_work',
        )

        person_changes = self._source.get_changed_person_ids(
            connection=connection,
            last_modified=person_modified,
            last_id=person_id,
            limit=self._batch_size,
        )

        film_work_changes = (
            self._source.get_changed_film_work_ids(
                connection=connection,
                last_modified=film_modified,
                last_id=film_id,
                limit=self._batch_size,
            )
        )

        if not (
            person_changes
            or film_work_changes
        ):
            logger.info(
                'Изменения для индекса персон не найдены.',
            )
            return False

        person_ids = {
            record.id
            for record in person_changes
        }

        if film_work_changes:
            changed_film_ids = [
                record.id
                for record in film_work_changes
            ]

            related_person_ids = (
                self._source.get_person_ids_by_film_work_ids(
                    connection=connection,
                    film_work_ids=changed_film_ids,
                )
            )

            person_ids.update(related_person_ids)

        if person_ids:
            postgres_persons = self._source.get_persons_by_ids(
                connection=connection,
                person_ids=sorted(person_ids),
            )

            person_documents = transform_persons(
                postgres_persons,
            )

            self._loader.bulk_load(
                index_name=self._index_name,
                documents=person_documents,
            )

        state_updates: StateData = {}

        state_updates.update(
            self._get_cursor_update(
                prefix='person',
                records=person_changes,
            ),
        )
        state_updates.update(
            self._get_cursor_update(
                prefix='film_work',
                records=film_work_changes,
            ),
        )

        self._state.set_states(state_updates)

        logger.info(
            'Итерация пайплайна персон завершена.',
        )

        return True
