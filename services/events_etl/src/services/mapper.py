"""Преобразование Kafka-событий в строки ClickHouse."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import orjson
from kafka.base import ConsumedMessage
from models.events import KafkaUserEvent
from models.rows import ClickHouseEventRow
from pydantic import ValidationError
from services.exceptions import EventMappingError


class EventMapper:
    """Преобразует пользовательские события в строки ClickHouse."""

    def map_batch(
        self,
        messages: list[ConsumedMessage],
    ) -> list[ClickHouseEventRow]:
        """Преобразовать пакет Kafka-сообщений в строки ClickHouse."""
        ingested_at = datetime.now(
            timezone.utc,
        )

        return [
            self.map_message(
                message,
                ingested_at=ingested_at,
            )
            for message in messages
        ]

    def map_message(
        self,
        message: ConsumedMessage,
        *,
        ingested_at: datetime,
    ) -> ClickHouseEventRow:
        """Преобразовать одно Kafka-сообщение в строку ClickHouse."""
        event = self._parse_event(
            message,
        )

        specific_fields = self._extract_specific_fields(
            event,
        )

        return ClickHouseEventRow(
            schema_version=event.schema_version,
            event_id=event.event_id,
            event_type=event.event_type,
            session_id=event.session_id,
            user_id=event.user_id,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            request_id=event.request_id,
            page=event.context.page,
            entity_type=(
                event.context.entity_type.value
                if event.context.entity_type is not None
                else None
            ),
            entity_id=event.context.entity_id,
            playback_id=event.playback_id,
            payload_json=(
                orjson.dumps(
                    event.payload,
                ).decode("utf-8")
            ),
            kafka_topic=message.topic,
            kafka_partition=message.partition,
            kafka_offset=message.offset,
            ingested_at=ingested_at,
            **specific_fields,
        )

    @staticmethod
    def _parse_event(
        message: ConsumedMessage,
    ) -> KafkaUserEvent:
        """Десериализовать и проверить пользовательское событие."""
        if message.value is None:
            raise EventMappingError(
                "Kafka message не содержит value: "
                f"topic={message.topic} "
                f"partition={message.partition} "
                f"offset={message.offset}"
            )

        try:
            raw_event = orjson.loads(
                message.value,
            )

        except orjson.JSONDecodeError as exc:
            raise EventMappingError(
                "Kafka message содержит некорректный JSON: "
                f"topic={message.topic} "
                f"partition={message.partition} "
                f"offset={message.offset}"
            ) from exc

        try:
            return KafkaUserEvent.model_validate(
                raw_event,
            )

        except ValidationError as exc:
            raise EventMappingError(
                "Kafka message не соответствует "
                "контракту пользовательского события: "
                f"topic={message.topic} "
                f"partition={message.partition} "
                f"offset={message.offset}"
            ) from exc

    def _extract_specific_fields(
        self,
        event: KafkaUserEvent,
    ) -> dict[str, Any]:
        """Извлечь специфичные для типа события поля."""
        fields: dict[str, Any] = {
            "element_type": None,
            "element_id": None,
            "target_url": None,
            "referrer": None,
            "position_seconds": None,
            "duration_seconds": None,
            "from_quality": None,
            "to_quality": None,
            "genre_id": None,
            "sort": None,
            "search_query": None,
        }

        match event.event_type:
            case "click":
                fields.update(
                    self._extract_click_fields(
                        event.payload,
                    )
                )

            case "page_view":
                fields.update(
                    self._extract_page_view_fields(
                        event.payload,
                    )
                )

            case "video_started":
                fields["duration_seconds"] = self._require_float(
                    event.payload,
                    "duration_seconds",
                )

            case "video_progress":
                fields["position_seconds"] = self._require_float(
                    event.payload,
                    "position_seconds",
                )

                fields["duration_seconds"] = self._require_float(
                    event.payload,
                    "duration_seconds",
                )

            case "video_finished":
                fields["duration_seconds"] = self._require_float(
                    event.payload,
                    "duration_seconds",
                )

            case "video_quality_changed":
                fields["position_seconds"] = self._require_float(
                    event.payload,
                    "position_seconds",
                )

                fields["from_quality"] = self._require_string(
                    event.payload,
                    "from_quality",
                )

                fields["to_quality"] = self._require_string(
                    event.payload,
                    "to_quality",
                )

            case "search_filter_used":
                fields.update(
                    self._extract_search_fields(
                        event.payload,
                    )
                )

            case _:
                raise EventMappingError(
                    "Неизвестный тип пользовательского события: "
                    f"{event.event_type}"
                )

        return fields

    @classmethod
    def _extract_click_fields(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Извлечь данные события клика."""
        return {
            "element_type": (
                cls._require_string(
                    payload,
                    "element_type",
                )
            ),
            "element_id": (
                cls._optional_string(
                    payload,
                    "element_id",
                )
            ),
            "target_url": (
                cls._optional_string(
                    payload,
                    "target_url",
                )
            ),
        }

    @classmethod
    def _extract_page_view_fields(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Извлечь данные просмотра страницы."""
        return {
            "referrer": cls._optional_string(
                payload,
                "referrer",
            ),
        }

    @classmethod
    def _extract_search_fields(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Извлечь параметры поиска и фильтрации."""
        filters = payload.get(
            "filters",
        )

        if not isinstance(filters, dict):
            raise EventMappingError(
                "search_filter_used должен содержать объект filters"
            )

        genre_id = filters.get(
            "genre_id",
        )

        try:
            parsed_genre_id = (
                UUID(str(genre_id)) if genre_id is not None else None
            )

        except ValueError as exc:
            raise EventMappingError(
                "genre_id содержит некорректный UUID"
            ) from exc

        return {
            "genre_id": parsed_genre_id,
            "sort": cls._optional_string(
                filters,
                "sort",
            ),
            "search_query": (
                cls._optional_string(
                    filters,
                    "query",
                )
            ),
        }

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
    ) -> str:
        """Получить обязательное строковое поле payload."""
        value = payload.get(key)

        if not isinstance(value, str) or not value:
            raise EventMappingError(f"Поле {key} должно быть непустой строкой")

        return value

    @staticmethod
    def _optional_string(
        payload: dict[str, Any],
        key: str,
    ) -> str | None:
        """Получить необязательное строковое поле payload."""
        value = payload.get(key)

        if value is None:
            return None

        if not isinstance(value, str):
            raise EventMappingError(f"Поле {key} должно быть строкой")

        return value

    @staticmethod
    def _require_float(
        payload: dict[str, Any],
        key: str,
    ) -> float:
        """Получить обязательное числовое поле payload."""
        value = payload.get(key)

        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise EventMappingError(f"Поле {key} должно быть числом")

        return float(value)
