"""Основной ETL-сервис оркестрации."""
import logging
import time

from psycopg2 import InterfaceError, OperationalError
from redis import Redis

from postgres_to_es.backoff import backoff
from postgres_to_es.config import get_settings
from postgres_to_es.elastic import ElasticsearchLoader
from postgres_to_es.pipelines import FilmsPipeline
from postgres_to_es.pipelines import GenresPipeline
from postgres_to_es.pipelines import PersonsPipeline
from postgres_to_es.postgres import PostgresExtractor
from postgres_to_es.state import RedisStorage, State

logger = logging.getLogger(__name__)


class ETLService:
    """Сервис для орекстрации ETL-пайплайнов."""
    def __init__(self):
        """Инициализирует ETL-зависимости и пайплайны."""
        self.settings = get_settings()

        self.redis_adapter = Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=(
                self.settings.redis_socket_connect_timeout
            ),
            socket_timeout=self.settings.redis_socket_timeout,
        )

        self.postgres = PostgresExtractor()
        self.elasticsearch = ElasticsearchLoader()

        self.films_pipeline = FilmsPipeline(
            postgres=self.postgres,
            elasticsearch=self.elasticsearch,
            state=self._create_state('films'),
            settings=self.settings,
        )

        self.genres_pipeline = GenresPipeline(
            postgres=self.postgres,
            elasticsearch=self.elasticsearch,
            state=self._create_state('genres'),
            settings=self.settings,
        )

        self.persons_pipeline = PersonsPipeline(
            postgres=self.postgres,
            elasticsearch=self.elasticsearch,
            state=self._create_state('persons'),
            settings=self.settings,
        )

    def run(self) -> None:
        """Запускает бесконечный ETL-процесс."""
        self._prepare_indices()

        while True:
            has_changes = self.run_iteration()

            if not has_changes:
                logger.info('No changes found')
                time.sleep(self.settings.etl_sleep_time)

    @backoff(exceptions=(InterfaceError, OperationalError))
    def run_iteration(self) -> bool:
        """Запускает одну итерацию для всех пайплайнов."""
        with self.postgres.connection() as connection:
            films_has_changes = self.films_pipeline.run_iteration(connection)
            genres_has_changes = self.genres_pipeline.run_iteration(connection)
            persons_has_changes = self.persons_pipeline.run_iteration(
                connection,
            )

        return films_has_changes or genres_has_changes or persons_has_changes

    def _prepare_indices(self) -> None:
        """Создает Elasticsearch индекс если их еще нет."""
        self.films_pipeline.prepare()
        self.genres_pipeline.prepare()
        self.persons_pipeline.prepare()

    def _create_state(self, pipeline_name: str) -> State:
        """Создает изолированное хранилище состояния
        для одного пайплайна."""
        return State(
            RedisStorage(
                redis_adapter=self.redis_adapter,
                state_key=self.settings.get_state_key(pipeline_name),
            ),
        )
