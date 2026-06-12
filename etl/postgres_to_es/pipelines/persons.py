"""Пайплайн загрузки персон в Elasticsearch."""
import logging
from typing import Any

from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.state import StateData
from postgres_to_es.transforms import transform_persons

logger = logging.getLogger(__name__)


class PersonsPipeline(BasePipeline):
    """Пайплайн загрузки индекса персон."""

    def prepare(self) -> None:
        """Создаёт индекс персон, если он ещё не существует."""
        self.elasticsearch.create_index_if_not_exists(
            index_name=self.settings.persons_index,
            schema_filename='persons_schema.json',
        )

    def run_iteration(self, connection: Any) -> bool:
        """Выполняет одну итерацию загрузки персон."""
        person_changes = self.postgres.get_changed_person_ids(
            connection=connection,
            last_modified=self._get_state('person_modified'),
            last_id=self._get_state('person_id'),
            limit=self.settings.batch_size,
        )

        film_work_changes = self.postgres.get_changed_film_work_ids(
            connection=connection,
            last_modified=self._get_state('film_work_modified'),
            last_id=self._get_state('film_work_id'),
            limit=self.settings.batch_size,
        )

        has_changes = bool(person_changes or film_work_changes)

        if not has_changes:
            logger.info('Изменения для индекса персон не найдены.')
            return False

        person_ids = {record.id for record in person_changes}

        if film_work_changes:
            film_work_ids = [record.id for record in film_work_changes]
            person_ids.update(
                self.postgres.get_person_ids_by_film_work_ids(
                    connection=connection,
                    film_work_ids=film_work_ids,
                ),
            )

        if person_ids:
            postgres_persons = self.postgres.get_persons_by_ids(
                connection=connection,
                person_ids=list(person_ids),
            )
            elastic_persons = transform_persons(postgres_persons)

            self.elasticsearch.bulk_load(
                index_name=self.settings.persons_index,
                documents=elastic_persons,
            )

        state_updates: StateData = {}
        state_updates.update(
            self._get_cursor_update('person', person_changes),
        )
        state_updates.update(
            self._get_cursor_update('film_work', film_work_changes),
        )

        if state_updates:
            self.state.set_states(state_updates)

        logger.info('Итерация пайплайна персон завершена.')
        return True
