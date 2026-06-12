"""Пайплайн загрузки жанров в Elasticsearch."""
import logging
from typing import Any

from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.transforms import transform_genres

logger = logging.getLogger(__name__)


class GenresPipeline(BasePipeline):
    """Пайплайн загрузки индекса жанров."""
    def prepare(self) -> None:
        """Создаёт индекс жанров, если он ещё не существует."""
        self.elasticsearch.create_index_if_not_exists(
            index_name=self.settings.genres_index,
            schema_filename='genres_schema.json',
        )

    def run_iteration(self, connection: Any) -> bool:
        """Выполняет одну итерацию загрузки жанров."""
        genre_changes = self.postgres.get_changed_genre_ids(
            connection=connection,
            last_modified=self._get_state('genre_modified'),
            last_id=self._get_state('genre_id'),
            limit=self.settings.batch_size,
        )

        if not genre_changes:
            logger.info('Изменения для индекса жанров не найдены.')
            return False

        genre_ids = [record.id for record in genre_changes]

        postgres_genres = self.postgres.get_genres_by_ids(
            connection=connection,
            genre_ids=genre_ids,
        )
        elastic_genres = transform_genres(postgres_genres)

        self.elasticsearch.bulk_load(
            index_name=self.settings.genres_index,
            documents=elastic_genres,
        )

        state_updates = self._get_cursor_update('genre', genre_changes)
        if state_updates:
            self.state.set_states(state_updates)

        logger.info('Итерация пайплайна жанров завершена.')
        return True
