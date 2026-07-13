"""Пайплайн загрузки жанров в целевой индекс."""
import logging

from psycopg2.extensions import connection as PgConnection

from postgres_to_es.interfaces import (
    DocumentLoader,
    GenresSource,
)
from postgres_to_es.pipelines.base import BasePipeline
from postgres_to_es.state import State
from postgres_to_es.transforms import transform_genres

logger = logging.getLogger(__name__)

GENRES_SCHEMA_FILENAME = 'genres.json'


class GenresPipeline(BasePipeline):
    """Загружает документы жанров."""
    def __init__(
        self,
        source: GenresSource,
        loader: DocumentLoader,
        state: State,
        index_name: str,
        batch_size: int,
    ) -> None:
        """Инициализирует пайплайн жанров."""
        super().__init__(
            loader=loader,
            state=state,
            index_name=index_name,
            schema_filename=GENRES_SCHEMA_FILENAME,
            batch_size=batch_size,
        )

        self._source = source

    def run_iteration(
        self,
        connection: PgConnection,
    ) -> bool:
        """Выполняет одну итерацию загрузки жанров."""
        genre_modified, genre_id = self._get_cursor(
            'genre',
        )

        genre_changes = self._source.get_changed_genre_ids(
            connection=connection,
            last_modified=genre_modified,
            last_id=genre_id,
            limit=self._batch_size,
        )

        if not genre_changes:
            logger.info(
                'Изменения для индекса жанров не найдены.',
            )
            return False

        genre_ids = [
            record.id
            for record in genre_changes
        ]

        postgres_genres = self._source.get_genres_by_ids(
            connection=connection,
            genre_ids=genre_ids,
        )

        genre_documents = transform_genres(
            postgres_genres,
        )

        self._loader.bulk_load(
            index_name=self._index_name,
            documents=genre_documents,
        )

        state_updates = self._get_cursor_update(
            prefix='genre',
            records=genre_changes,
        )

        self._state.set_states(state_updates)

        logger.info(
            'Итерация пайплайна жанров завершена.',
        )

        return True
