"""Модели пользовательских событий, получаемых из Kafka."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Тип сущности онлайн-кинотеатра."""

    MOVIE = "movie"
    GENRE = "genre"
    PERSON = "person"


class EventContext(BaseModel):
    """Контекст пользовательского события."""

    model_config = ConfigDict(extra="forbid")

    page: str
    entity_type: EntityType | None = None
    entity_id: UUID | None = None


class KafkaUserEvent(BaseModel):
    """Пользовательское событие, полученное из Kafka."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]

    event_id: UUID
    event_type: str

    session_id: UUID
    user_id: UUID | None = None

    occurred_at: datetime
    received_at: datetime

    request_id: str

    context: EventContext

    playback_id: UUID | None = None

    payload: dict[str, Any] = Field(
        default_factory=dict,
    )
