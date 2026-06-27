"""Загрузчик документов в Elasticsearch."""

import json
import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

from elastic_transport import (
    ConnectionError as ElasticsearchConnectionError,
    ConnectionTimeout as ElasticsearchConnectionTimeout,
)
from elasticsearch import Elasticsearch

from postgres_to_es.backoff import retryable
from postgres_to_es.interfaces import DocumentLoader, RetryExecutor
from postgres_to_es.models import BaseDocument

logger = logging.getLogger(__name__)


class IndexSchema(TypedDict):
    """Структура схемы индекса Elasticsearch."""

    settings: dict[str, Any]
    mappings: dict[str, Any]


class ElasticsearchLoader(DocumentLoader):
    """Создаёт индексы и загружает документы в Elasticsearch."""
    def __init__(
        self,
        client: Elasticsearch,
        schemas_dir: Path,
        retry_executor: RetryExecutor,
    ) -> None:
        """Инициализирует загрузчик с готовым клиентом Elasticsearch."""
        self._client = client
        self._schemas_dir = schemas_dir
        self._retry_executor = retry_executor

    @retryable(
        exceptions=(
            ElasticsearchConnectionError,
            ElasticsearchConnectionTimeout,
        ),
    )
    def create_index_if_not_exists(
        self,
        index_name: str,
        schema_filename: str,
    ) -> None:
        """Создаёт индекс Elasticsearch, если он отсутствует."""
        if self._client.indices.exists(index=index_name):
            logger.info(
                'Индекс Elasticsearch %s уже существует.',
                index_name,
            )
            return

        schema = self._load_index_schema(schema_filename)

        self._client.indices.create(
            index=index_name,
            settings=schema['settings'],
            mappings=schema['mappings'],
        )

        logger.info(
            'Индекс Elasticsearch %s создан.',
            index_name,
        )

    @retryable(
        exceptions=(
            ElasticsearchConnectionError,
            ElasticsearchConnectionTimeout,
        ),
    )
    def bulk_load(
        self,
        index_name: str,
        documents: Sequence[BaseDocument],
    ) -> None:
        """Загружает последовательность документов через Bulk API."""
        if not documents:
            logger.info(
                'Нет документов для загрузки в индекс %s.',
                index_name,
            )
            return

        operations = self._build_bulk_operations(
            index_name=index_name,
            documents=documents,
        )

        response = self._client.bulk(
            operations=operations,
            refresh=False,
        )

        response_body = response.body

        if not isinstance(response_body, Mapping):
            raise RuntimeError(
                'Elasticsearch вернул некорректный ответ Bulk API.',
            )

        if response_body.get('errors'):
            errors = self._extract_bulk_errors(response_body)

            raise RuntimeError(
                f'Ошибка bulk-загрузки в Elasticsearch: {errors}',
            )

        logger.info(
            'Загружено %s документов в индекс %s.',
            len(documents),
            index_name,
        )

    def _load_index_schema(
        self,
        schema_filename: str,
    ) -> IndexSchema:
        """Читает и проверяет JSON-схему индекса."""
        schema_path = self._schemas_dir / schema_filename

        with schema_path.open(
            mode='r',
            encoding='utf-8',
        ) as file:
            raw_schema: Any = json.load(file)

        if not isinstance(raw_schema, dict):
            raise ValueError(
                f'Схема {schema_path} должна быть JSON-объектом.',
            )

        settings = raw_schema.get('settings')
        mappings = raw_schema.get('mappings')

        if not isinstance(settings, dict):
            raise ValueError(
                f'В схеме {schema_path} отсутствует объект settings.',
            )

        if not isinstance(mappings, dict):
            raise ValueError(
                f'В схеме {schema_path} отсутствует объект mappings.',
            )

        return {
            'settings': settings,
            'mappings': mappings,
        }

    @staticmethod
    def _build_bulk_operations(
        index_name: str,
        documents: Sequence[BaseDocument],
    ) -> list[Mapping[str, Any]]:
        """Формирует операции для Elasticsearch Bulk API."""
        operations: list[Mapping[str, Any]] = []

        for document in documents:
            operations.append(
                {
                    'index': {
                        '_index': index_name,
                        '_id': document.uuid,
                    },
                },
            )

            operations.append(
                document.model_dump(mode='json'),
            )

        return operations

    @staticmethod
    def _extract_bulk_errors(
        response: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Извлекает информацию об ошибках отдельных операций."""
        errors: list[dict[str, Any]] = []
        items = response.get('items', [])

        if not isinstance(items, list):
            return [
                {
                    'reason': (
                        'Поле items в ответе Bulk API '
                        'имеет некорректный формат.'
                    ),
                },
            ]

        for item in items:
            if not isinstance(item, Mapping):
                continue

            index_result = item.get('index')

            if not isinstance(index_result, Mapping):
                continue

            error = index_result.get('error')

            if not isinstance(error, Mapping):
                continue

            errors.append(
                {
                    '_id': index_result.get('_id'),
                    'status': index_result.get('status'),
                    'type': error.get('type'),
                    'reason': error.get('reason'),
                },
            )

        return errors
