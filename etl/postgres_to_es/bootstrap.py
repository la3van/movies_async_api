"""Сборка зависимостей ETL-приложения."""
from collections.abc import Iterator
from contextlib import contextmanager

from elasticsearch import Elasticsearch
from redis import Redis

from postgres_to_es.backoff import (
    BackoffPolicy,
    BackoffRetryExecutor,
)
from postgres_to_es.config import get_settings
from postgres_to_es.interfaces import RetryExecutor
from postgres_to_es.loaders import ElasticsearchLoader
from postgres_to_es.pipelines import (
    FilmsPipeline,
    GenresPipeline,
    PersonsPipeline,
)
from postgres_to_es.service import ETLService
from postgres_to_es.sources import PostgresSource
from postgres_to_es.state import RedisStateStorage, State


def _create_state(
    redis_adapter: Redis,
    state_key: str,
    retry_executor: RetryExecutor,
) -> State:
    """Создаёт изолированное состояние одного ETL-пайплайна."""
    storage = RedisStateStorage(
        redis_adapter=redis_adapter,
        state_key=state_key,
        retry_executor=retry_executor,
    )

    return State(storage=storage)


@contextmanager
def build_etl_service() -> Iterator[ETLService]:
    """Создаёт ETL-сервис и управляет внешними ресурсами."""
    settings = get_settings()

    retry_policy = BackoffPolicy(
        start_sleep_time=settings.backoff_start_sleep_time,
        factor=settings.backoff_factor,
        max_sleep_time=settings.backoff_border_sleep_time,
        jitter=settings.backoff_jitter,
    )

    retry_executor = BackoffRetryExecutor(
        policy=retry_policy,
    )

    redis_adapter = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
        socket_connect_timeout=(
            settings.redis_socket_connect_timeout
        ),
        socket_timeout=settings.redis_socket_timeout,
    )

    elastic_client: Elasticsearch | None = None

    try:
        elastic_client = Elasticsearch(
            hosts=[settings.elastic_url],
            request_timeout=settings.elastic_request_timeout,
        )

        postgres_source = PostgresSource(
            connection_params=settings.postgres_connection_params,
        )

        document_loader = ElasticsearchLoader(
            client=elastic_client,
            schemas_dir=settings.schemas_dir,
            retry_executor=retry_executor,
        )

        films_state = _create_state(
            redis_adapter=redis_adapter,
            state_key=settings.get_state_key('films'),
            retry_executor=retry_executor,
        )

        genres_state = _create_state(
            redis_adapter=redis_adapter,
            state_key=settings.get_state_key('genres'),
            retry_executor=retry_executor,
        )

        persons_state = _create_state(
            redis_adapter=redis_adapter,
            state_key=settings.get_state_key('persons'),
            retry_executor=retry_executor,
        )

        films_pipeline = FilmsPipeline(
            source=postgres_source,
            loader=document_loader,
            state=films_state,
            index_name=settings.movies_index,
            batch_size=settings.batch_size,
        )

        genres_pipeline = GenresPipeline(
            source=postgres_source,
            loader=document_loader,
            state=genres_state,
            index_name=settings.genres_index,
            batch_size=settings.batch_size,
        )

        persons_pipeline = PersonsPipeline(
            source=postgres_source,
            loader=document_loader,
            state=persons_state,
            index_name=settings.persons_index,
            batch_size=settings.batch_size,
        )

        service = ETLService(
            connection_provider=postgres_source,
            pipelines=(
                films_pipeline,
                genres_pipeline,
                persons_pipeline,
            ),
            sleep_time=settings.etl_sleep_time,
            retry_executor=retry_executor,
        )

        yield service
    finally:
        if elastic_client is not None:
            elastic_client.close()

        redis_adapter.close()
