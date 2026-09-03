"""Доменные модели и правила валидации пользовательских событий."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    field_validator,
    model_validator,
)

MAX_FUTURE_EVENT_CLOCK_SKEW = timedelta(
    minutes=5,
)


class EntityType(str, Enum):
    """Тип сущности онлайн-кинотеатра, связанной с событием."""

    MOVIE = "movie"
    GENRE = "genre"
    PERSON = "person"


class EventContext(BaseModel):
    """Контекст страницы и сущности, с которыми связано событие."""

    model_config = ConfigDict(extra="forbid")

    page: str = Field(
        min_length=1,
        max_length=2048,
    )

    entity_type: EntityType | None = None
    entity_id: UUID | None = None

    @model_validator(mode="after")
    def validate_entity(self) -> "EventContext":
        """Проверить согласованность типа и идентификатора сущности."""
        has_entity_type = self.entity_type is not None
        has_entity_id = self.entity_id is not None

        if has_entity_type != has_entity_id:
            raise ValueError(
                "entity_type и entity_id должны быть указаны одновременно"
            )

        return self


class BaseEvent(BaseModel):
    """Общие поля любого пользовательского события."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1

    event_id: UUID
    event_type: str

    session_id: UUID
    user_id: UUID | None = None

    occurred_at: datetime

    context: EventContext

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(
        cls,
        value: datetime,
    ) -> datetime:
        """Проверить timezone и запретить сильно будущие события."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "occurred_at должен содержать информацию о часовом поясе"
            )

        value = value.astimezone(
            timezone.utc,
        )

        now = datetime.now(
            timezone.utc,
        )

        if value > now + MAX_FUTURE_EVENT_CLOCK_SKEW:
            raise ValueError(
                "occurred_at не может находиться в будущем "
                "более чем на 5 минут"
            )

        return value


class ClickPayload(BaseModel):
    """Дополнительные данные события клика."""

    model_config = ConfigDict(extra="forbid")

    element_type: str = Field(
        min_length=1,
        max_length=128,
    )

    element_id: str | None = Field(
        default=None,
        max_length=256,
    )

    target_url: str | None = Field(
        default=None,
        max_length=2048,
    )


class ClickEvent(BaseEvent):
    """Событие клика пользователя по элементу интерфейса."""

    event_type: Literal["click"] = "click"
    payload: ClickPayload


class PageViewPayload(BaseModel):
    """Дополнительные данные просмотра страницы."""

    model_config = ConfigDict(extra="forbid")

    referrer: str | None = Field(
        default=None,
        max_length=2048,
    )


class PageViewEvent(BaseEvent):
    """Событие просмотра пользователем страницы."""

    event_type: Literal["page_view"] = "page_view"
    payload: PageViewPayload


class VideoEvent(BaseEvent):
    """Базовая модель события, связанного с просмотром фильма."""

    playback_id: UUID

    @model_validator(mode="after")
    def validate_movie_context(self) -> "VideoEvent":
        """Проверить наличие фильма в контексте видео-события."""
        if self.context.entity_type != EntityType.MOVIE:
            raise ValueError("для видео-события entity_type должен быть movie")

        if self.context.entity_id is None:
            raise ValueError(
                "для видео-события должен быть указан entity_id фильма"
            )

        return self


class VideoStartedPayload(BaseModel):
    """Данные начала просмотра фильма."""

    model_config = ConfigDict(extra="forbid")

    duration_seconds: float = Field(gt=0)


class VideoStartedEvent(VideoEvent):
    """Событие начала просмотра фильма."""

    event_type: Literal["video_started"] = "video_started"
    payload: VideoStartedPayload


class VideoProgressPayload(BaseModel):
    """Данные о текущем прогрессе просмотра фильма."""

    model_config = ConfigDict(extra="forbid")

    position_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_position(self) -> "VideoProgressPayload":
        """Проверить, что позиция не превышает длительность фильма."""
        if self.position_seconds > self.duration_seconds:
            raise ValueError(
                "position_seconds не может превышать duration_seconds"
            )

        return self


class VideoProgressEvent(VideoEvent):
    """Событие изменения прогресса просмотра фильма."""

    event_type: Literal["video_progress"] = "video_progress"
    payload: VideoProgressPayload


class VideoFinishedPayload(BaseModel):
    """Данные завершённого просмотра фильма."""

    model_config = ConfigDict(extra="forbid")

    duration_seconds: float = Field(gt=0)


class VideoFinishedEvent(VideoEvent):
    """Событие завершённого просмотра фильма."""

    event_type: Literal["video_finished"] = "video_finished"
    payload: VideoFinishedPayload


class VideoQualityChangedPayload(BaseModel):
    """Данные изменения качества воспроизведения."""

    model_config = ConfigDict(extra="forbid")

    from_quality: str = Field(
        min_length=1,
        max_length=32,
    )
    to_quality: str = Field(
        min_length=1,
        max_length=32,
    )

    position_seconds: float = Field(ge=0)


class VideoQualityChangedEvent(VideoEvent):
    """Событие изменения качества воспроизведения фильма."""

    event_type: Literal["video_quality_changed"] = "video_quality_changed"

    payload: VideoQualityChangedPayload


class SearchFilters(BaseModel):
    """Параметры поиска и фильтрации фильмов, выбранные пользователем."""

    model_config = ConfigDict(extra="forbid")

    genre_id: UUID | None = None

    sort: (
        Literal[
            "imdb_rating",
            "-imdb_rating",
        ]
        | None
    ) = None

    query: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
    )

    @model_validator(mode="after")
    def validate_filters(self) -> "SearchFilters":
        """Проверить наличие хотя бы одного параметра поиска."""
        if self.genre_id is None and self.sort is None and self.query is None:
            raise ValueError("должен быть указан хотя бы один параметр поиска")

        return self


class SearchFilterPayload(BaseModel):
    """Данные события использования поиска или фильтрации фильмов."""

    model_config = ConfigDict(extra="forbid")

    filters: SearchFilters


class SearchFilterUsedEvent(BaseEvent):
    """Событие использования параметров поиска или фильтрации фильмов."""

    event_type: Literal["search_filter_used"] = "search_filter_used"

    payload: SearchFilterPayload


EventRequest = Annotated[
    (
        ClickEvent
        | PageViewEvent
        | VideoStartedEvent
        | VideoProgressEvent
        | VideoFinishedEvent
        | VideoQualityChangedEvent
        | SearchFilterUsedEvent
    ),
    Field(discriminator="event_type"),
]

EVENT_REQUEST_ADAPTER: TypeAdapter[EventRequest] = TypeAdapter(EventRequest)
