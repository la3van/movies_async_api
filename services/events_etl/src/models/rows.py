"""Модель строки пользовательского события для ClickHouse."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClickHouseEventRow(BaseModel):
    """Строка таблицы analytics.user_events."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int

    event_id: UUID
    event_type: str

    session_id: UUID
    user_id: UUID | None

    occurred_at: datetime
    received_at: datetime

    request_id: str

    page: str

    entity_type: str | None
    entity_id: UUID | None

    playback_id: UUID | None

    element_type: str | None = None
    element_id: str | None = None
    target_url: str | None = None

    referrer: str | None = None

    position_seconds: float | None = None
    duration_seconds: float | None = None
    from_quality: str | None = None
    to_quality: str | None = None

    genre_id: UUID | None = None
    sort: str | None = None
    search_query: str | None = None

    payload_json: str

    kafka_topic: str
    kafka_partition: int
    kafka_offset: int

    ingested_at: datetime
