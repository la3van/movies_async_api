CREATE DATABASE IF NOT EXISTS analytics;


CREATE TABLE IF NOT EXISTS analytics.user_events
(
    -- Общие поля события
    schema_version UInt16,
    event_id UUID,
    event_type LowCardinality(String),
    session_id UUID,
    user_id Nullable(UUID),
    occurred_at DateTime64(3, 'UTC'),
    received_at DateTime64(3, 'UTC'),
    request_id String,


    -- Контекст события
    page String,
    entity_type LowCardinality(Nullable(String)),
    entity_id Nullable(UUID),

    -- Конкретная попытка просмотра фильма
    playback_id Nullable(UUID),

    -- Click
    element_type LowCardinality(Nullable(String)),
    element_id Nullable(String),
    target_url Nullable(String),

    -- Page view
    referrer Nullable(String),

    -- Video events
    position_seconds Nullable(Float64),
    duration_seconds Nullable(Float64),
    from_quality LowCardinality(Nullable(String)),
    to_quality LowCardinality(Nullable(String)),

    -- Search/filter events
    genre_id Nullable(UUID),
    sort Nullable(String),
    search_query Nullable(String),

    -- Исходный payload на случай расширения схемы
    payload_json String,

    -- Метаданные Kafka
    kafka_topic LowCardinality(String),
    kafka_partition UInt16,
    kafka_offset UInt64,

    -- Время записи события ETL-сервисом
    ingested_at DateTime64(3, 'UTC')
        DEFAULT now64(3)
)
ENGINE = ReplacingMergeTree(received_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (
    event_type,
    occurred_at,
    event_id
);