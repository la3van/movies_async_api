# ETL service

Синхронный ETL-сервис, который инкрементально переносит фильмы, жанры и персоны из PostgreSQL в Elasticsearch.

## Стек

- Python 3.12;
- psycopg2;
- Elasticsearch Python client;
- Redis;
- Pydantic v2;
- pydantic-settings.

## Поток данных

```text
PostgreSQL
    ↓ extract
PostgresSource
    ↓
FilmsPipeline / GenresPipeline / PersonsPipeline
    ↓ transform
ElasticsearchLoader
    ↓ load
Elasticsearch

State ─────────► Redis DB 0
RetryExecutor ─► PostgreSQL, Elasticsearch и Redis operations
```

## Индексы

| Индекс | Пайплайн | Содержимое |
| --- | --- | --- |
| `movies` | `FilmsPipeline` | Фильмы, жанры и участники |
| `genres` | `GenresPipeline` | Жанры |
| `persons` | `PersonsPipeline` | Персоны, фильмы и роли |

JSON-схемы индексов находятся в корневом каталоге `schemas/` и монтируются в контейнер ETL как `/app/schemas`.

## Структура

```text
etl/
├── postgres_to_es/
│   ├── interfaces/          # Абстракции connection, source, loader и retry
│   ├── loaders/             # ElasticsearchLoader
│   ├── models/              # Модели PostgreSQL и Elasticsearch documents
│   ├── pipelines/           # Три инкрементальных пайплайна
│   ├── sources/             # PostgresSource и SQL-запросы
│   ├── state/               # State, StateStorage и RedisStateStorage
│   ├── transforms/          # Чистые преобразования моделей
│   ├── backoff.py           # Retry policy, executor и декоратор
│   ├── bootstrap.py         # Composition root
│   ├── config.py            # Settings
│   ├── main.py              # Entry point
│   └── service.py           # Оркестратор пайплайнов
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## SOLID-структура

Высокоуровневые компоненты зависят от интерфейсов:

```text
ETLService
    ├── ConnectionProvider
    ├── Sequence[BasePipeline]
    └── RetryExecutor

FilmsPipeline
    ├── FilmsSource
    ├── DocumentLoader
    └── State
```

`bootstrap.py` создаёт и связывает конкретные реализации:

- `PostgresSource`;
- `ElasticsearchLoader`;
- `RedisStateStorage`;
- `BackoffRetryExecutor`;
- три pipeline;
- `ETLService`.

## Состояние ETL

Для каждого пайплайна используется отдельный Redis key:

```text
etl_state:films
etl_state:genres
etl_state:persons
```

Состояние содержит курсоры `modified + id`. Курсор обновляется только после успешной загрузки пакета в Elasticsearch.

В основном Docker Compose используется Redis DB `0`.

## Exponential backoff

Временные ошибки внешних сервисов обрабатываются через:

- `BackoffPolicy` — параметры задержек;
- `BackoffRetryExecutor` — алгоритм повторов;
- `@retryable` — применение executor к методу.

Backoff применяется к:

- Redis state operations;
- Elasticsearch index и bulk operations;
- полной итерации ETL при ошибках PostgreSQL connection.

При повторе PostgreSQL-итерации создаётся новое соединение, а не используется повреждённое старое.

## Конфигурация

Создайте `.env`:

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

`POSTGRES_STATEMENT_TIMEOUT_MS` добавляется в PostgreSQL `options` и ограничивает длительность одного SQL-запроса.

## Запуск

Из корня проекта:

```bash
docker compose up --build etl
```

Для просмотра логов:

```bash
docker compose logs -f etl
```

Полный чистый запуск с повторной загрузкой данных:

```bash
docker compose down -v
docker compose up --build
```

Команда удаляет volumes PostgreSQL, Elasticsearch и Redis. Используйте её только когда действительно нужен чистый запуск.

## Проверка результата

```bash
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/movies/_count?pretty"
curl "http://localhost:9200/genres/_count?pretty"
curl "http://localhost:9200/persons/_count?pretty"
```

Проверка Redis state:

```bash
docker compose exec redis redis-cli --scan --pattern 'etl_state:*'
docker compose exec redis redis-cli GET 'etl_state:films'
```

## Локальный запуск

Из каталога `etl`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Укажите в `.env` адреса сервисов, доступные с хоста, и запустите:

```bash
python -m postgres_to_es.main
```

## Проверка типов

Из корня проекта:

```bash
mypy etl/postgres_to_es
```

## Ограничения текущего CDC

Пайплайны ориентируются на `modified` основных таблиц. Изменения или удаления только в таблицах связей `person_film_work` и `genre_film_work` требуют обновления `modified` родительских сущностей, триггеров либо отдельного change log/outbox механизма.
