"""Сервис оркестрации ETL-пайплайнов."""

import logging
import time
from collections.abc import Callable, Sequence

from psycopg2 import InterfaceError, OperationalError

from postgres_to_es.backoff import retryable
from postgres_to_es.interfaces import (
    ConnectionProvider,
    RetryExecutor,
)
from postgres_to_es.pipelines import BasePipeline

logger = logging.getLogger(__name__)


class ETLService:
    """Оркестрирует выполнение ETL-пайплайнов."""
    def __init__(
        self,
        connection_provider: ConnectionProvider,
        pipelines: Sequence[BasePipeline],
        sleep_time: float,
        retry_executor: RetryExecutor,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        """Сохраняет зависимости ETL-сервиса."""
        if sleep_time < 0:
            raise ValueError(
                'Время ожидания ETL не может быть отрицательным.',
            )

        self._connection_provider = connection_provider
        self._pipelines = tuple(pipelines)
        self._sleep_time = sleep_time
        self._retry_executor = retry_executor
        self._sleeper = sleeper

    def run(self) -> None:
        """Запускает непрерывное выполнение ETL."""
        self._prepare_pipelines()

        while True:
            has_changes = self.run_iteration()

            if not has_changes:
                logger.info(
                    'Изменения не найдены. Ожидание следующей итерации.',
                )
                self._sleeper(self._sleep_time)

    @retryable(
        exceptions=(
            InterfaceError,
            OperationalError,
        ),
    )
    def run_iteration(self) -> bool:
        """Выполняет одну итерацию всех пайплайнов."""
        with self._connection_provider.connection() as connection:
            results = [
                pipeline.run_iteration(connection)
                for pipeline in self._pipelines
            ]

        return any(results)

    def _prepare_pipelines(self) -> None:
        """Подготавливает целевые ресурсы пайплайнов."""
        for pipeline in self._pipelines:
            pipeline.prepare()
