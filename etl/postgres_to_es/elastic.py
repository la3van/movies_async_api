"""Модуль для загрузки данных в Elasticsearch."""
import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from elastic_transport import (
    ConnectionError as ElasticsearchConnectionError,
    ConnectionTimeout as ElasticsearchConnectionTimeout,
)
from elasticsearch import Elasticsearch
from pydantic import BaseModel

from postgres_to_es.backoff import backoff
from postgres_to_es.config import get_settings

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).resolve().parent / 'schemas'


class ElasticsearchLoader:
    """Класс для работы с Elasticsearch."""
    def __init__(self) -> None:
        """Инициализирует клиент Elasticsearch."""
        self.settings = get_settings()
        self.client = Elasticsearch(
            hosts=[self.settings.elastic_url],
            request_timeout=self.settings.elastic_request_timeout,
        )

    @backoff(
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
        """Создаёт индекс Elasticsearch, если он ещё не существует."""
        if self.client.indices.exists(index=index_name):
            logger.info('Индекс Elasticsearch %s уже существует.', index_name)
            return

        schema = self._load_index_schema(schema_filename)

        self.client.indices.create(
            index=index_name,
            settings=schema['settings'],
            mappings=schema['mappings'],
        )

        logger.info('Индекс Elasticsearch %s создан.', index_name)

    def _load_index_schema(self, schema_filename: str) -> dict[str, Any]:
        """Загружает схему индекса Elasticsearch из JSON-файла."""
        schema_path = SCHEMAS_DIR / schema_filename

        with schema_path.open('r', encoding='utf-8') as file:
            schema: dict[str, Any] = json.load(file)

        return schema

    @backoff(
        exceptions=(
            ElasticsearchConnectionError,
            ElasticsearchConnectionTimeout,
        ),
    )
    def bulk_load(
        self,
        index_name: str,
        documents: list[BaseModel],
    ) -> None:
        """Загружает документы в Elasticsearch через Bulk API."""
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

        response = self.client.options(
            request_timeout=self.settings.elastic_request_timeout,
        ).bulk(
            operations=operations,
            refresh=False,
        )

        response_body = response.body

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

    def _build_bulk_operations(
        self,
        index_name: str,
        documents: list[BaseModel],
    ) -> list[Mapping[str, Any]]:
        """Формирует операции для Elasticsearch Bulk API."""
        operations: list[Mapping[str, Any]] = []

        for document in documents:
            document_data = document.model_dump(mode='json')

            operations.append(
                {
                    'index': {
                        '_index': index_name,
                        '_id': document_data['uuid'],
                    },
                },
            )
            operations.append(document_data)

        return operations

    def _extract_bulk_errors(
        self,
        response: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Достаёт ошибки из ответа Elasticsearch Bulk API."""
        errors: list[dict[str, Any]] = []

        for item in response.get('items', []):
            index_result = item.get('index', {})
            error = index_result.get('error')

            if error:
                errors.append(
                    {
                        '_id': index_result.get('_id'),
                        'status': index_result.get('status'),
                        'type': error.get('type'),
                        'reason': error.get('reason'),
                    },
                )

        return errors

    def close(self) -> None:
        """Закрывает соединение с Elasticsearch."""
        self.client.close()
