# Content ETL

Синхронный фоновый процесс, который инкрементально переносит фильмы, жанры и персоны из PostgreSQL в Elasticsearch.

Content ETL не предоставляет HTTP API и запускается как отдельный Docker Compose service `content-etl`.

## Стек

- Python 3.12;
- psycopg2;
- Elasticsearch Python client;
- Redis;
- Pydantic v2;
- pydantic-settings.

## Поток данных

```text
PostgreSQL theatre
    ↓ extract
PostgresSource
    ↓
FilmsPipeline / GenresPipeline / PersonsPipeline
    ↓ transform
ElasticsearchLoader
    ↓ load
Elasticsearch

Pipeline state ─────► Redis DB 0
RetryExecutor ──────► PostgreSQL, Elasticsearch и Redis operations
```

## Индексы

| Индекс | Pipeline | Содержимое |
| --- | --- | --- |
| `movies` | `FilmsPipeline` | Фильмы, жанры и участники |
| `genres` | `GenresPipeline` | Жанры |
| `persons` | `PersonsPipeline` | Персоны, фильмы и роли |

Mappings находятся в [`../../infrastructure/elasticsearch/mappings`](../../infrastructure/elasticsearch/mappings) и монтируются в контейнер как `/app/mappings`.

## Структура

```text
content_etl/
├── postgres_to_es/
│   ├── interfaces/          # контракты connection, source, loader и retry
│   ├── loaders/             # загрузка документов в Elasticsearch
│   ├── models/              # PostgreSQL-модели и Elasticsearch documents
│   ├── pipelines/           # films, genres и persons pipelines
│   ├── sources/             # чтение PostgreSQL и SQL-запросы
│   ├── state/               # Redis state storage
│   ├── transforms/          # чистые преобразования моделей
│   ├── backoff.py
│   ├── bootstrap.py
│   ├── config.py
│   ├── main.py
│   └── service.py
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

## Composition root

`bootstrap.py` создаёт и связывает:

- `PostgresSource`;
- `ElasticsearchLoader`;
- `RedisStateStorage`;
- `BackoffRetryExecutor`;
- три pipelines;
- `ETLService`.

Высокоуровневые компоненты зависят от интерфейсов, а не от конкретных реализаций.

## Состояние ETL

Для pipelines используются отдельные Redis keys:

```text
etl_state:films
etl_state:genres
etl_state:persons
```

Состояние содержит курсор `modified + id`. Он обновляется только после успешной загрузки пакета в Elasticsearch.

В корневом Docker Compose используется Redis DB `0`.

## Exponential backoff

Retry-механизм включает:

- `BackoffPolicy` — параметры задержек;
- `BackoffRetryExecutor` — выполнение повторов;
- `@retryable` — применение executor к операции.

Backoff применяется к:

- Redis state operations;
- созданию индексов и bulk-загрузке Elasticsearch;
- итерациям ETL при ошибках PostgreSQL connection.

При повторе PostgreSQL-итерации создаётся новое соединение.

## Конфигурация

Из каталога `services/content_etl`:

```bash
cp .env.example .env
```

Основные настройки:

```env
POSTGRES_HOST=theatre-db
POSTGRES_PORT=5432
POSTGRES_DB=theatre
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_OPTIONS="-c search_path=public,content"
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_STATEMENT_TIMEOUT_MS=30000

ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_REQUEST_TIMEOUT=30
MOVIES_INDEX=movies
GENRES_INDEX=genres
PERSONS_INDEX=persons
SCHEMAS_DIR=/app/mappings

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_STATE_KEY_PREFIX=etl_state
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

BATCH_SIZE=100
ETL_SLEEP_TIME=1

BACKOFF_START_SLEEP_TIME=0.1
BACKOFF_FACTOR=2
BACKOFF_BORDER_SLEEP_TIME=10
BACKOFF_JITTER=true
```

Имя `SCHEMAS_DIR` сохранено в конфигурации, хотя каталог содержит Elasticsearch mappings.

## Запуск

Из корня репозитория:

```bash
docker compose up --build content-etl
```

Логи:

```bash
docker compose logs -f content-etl
```

Полный чистый запуск:

```bash
docker compose down -v
docker compose up --build
```

Команда удаляет данные PostgreSQL, Elasticsearch и Redis.

## Наблюдаемость

В текущей конфигурации Content ETL не экспортирует OpenTelemetry traces в Jaeger. Распределённая трассировка настроена для HTTP-приложений `content-service`, `auth-service` и `admin-service`.

ETL диагностируется по собственным логам, состоянию Redis и результатам загрузки Elasticsearch:

```bash
docker compose logs -f content-etl
docker compose exec redis redis-cli --scan --pattern 'etl_state:*'
curl "http://localhost:9200/_cat/indices?v"
```

Если трассировка фонового процесса будет добавлена позднее, полезными границами spans будут отдельная итерация ETL, обработка batch и retry-попытка, а не каждая чистая transform-функция.

## Проверка результата

```bash
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/movies/_count?pretty"
curl "http://localhost:9200/genres/_count?pretty"
curl "http://localhost:9200/persons/_count?pretty"
```

Состояние Redis:

```bash
docker compose exec redis redis-cli --scan --pattern 'etl_state:*'
docker compose exec redis redis-cli GET 'etl_state:films'
```

## Локальный запуск

Из каталога `services/content_etl`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m postgres_to_es.main
```

В `.env` должны быть указаны адреса PostgreSQL, Elasticsearch и Redis, доступные с хоста.

## Проверка типов

Из корня репозитория:

```bash
mypy services/content_etl/postgres_to_es
```

## Maintainability Index

```bash
radon mi services/content_etl/postgres_to_es -s
```

Актуальные результаты проекта хранятся в [`../../docs/CODE_MAINTAINABILITY.md`](../../docs/CODE_MAINTAINABILITY.md).

## Ограничения текущего CDC

Pipelines ориентируются на `modified` основных таблиц. Изменения только в таблицах связей `person_film_work` и `genre_film_work` требуют обновления `modified` родительской сущности, триггеров либо отдельного change log/outbox механизма.
