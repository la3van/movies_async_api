# Movies Async API

Read-only backend для онлайн-кинотеатра. Проект переносит данные о фильмах, жанрах и персонах из PostgreSQL в Elasticsearch и предоставляет HTTP API для поиска и чтения этих данных.

## Архитектура

```text
PostgreSQL
    │
    ▼
ETL service ───────► Redis DB 0
    │                состояние пайплайнов
    ▼
Elasticsearch
    ▲
    │
Async API ─────────► Redis DB 1
    │                кеш ответов
    ▼
HTTP client
```

В проект входят следующие сервисы:

| Сервис | Назначение |
| --- | --- |
| `theatre-db` | PostgreSQL с исходными данными |
| `etl` | Инкрементальный перенос данных PostgreSQL → Elasticsearch |
| `elasticsearch` | Read-модель и полнотекстовый поиск |
| `redis` | Состояние ETL и кеш Async API |
| `async_api` | Read-only API на FastAPI |

## Основные возможности

- получение фильмов, жанров и персон по UUID;
- пагинация и сортировка списков;
- фильтрация фильмов по жанру;
- полнотекстовый поиск по фильмам, жанрам и персонам;
- поиск похожих фильмов;
- получение фильмов, связанных с персоной;
- кеширование ответов API в Redis;
- инкрементальная ETL-загрузка трёх Elasticsearch-индексов;
- exponential backoff для внешних зависимостей ETL;
- встроенные retries и exponential backoff для Redis и Elasticsearch в Async API;
- функциональные тесты с отдельными Elasticsearch и Redis.

## Технологии

- FastAPI и Uvicorn;
- PostgreSQL 16;
- Elasticsearch 9.4.2;
- Elasticsearch Python client 9.4.1;
- Redis 7 и redis-py 7.1.0;
- Pydantic v2 и pydantic-settings;
- psycopg2;
- pytest, pytest-asyncio и aiohttp;
- Docker Compose;
- mypy, coverage.py и Radon.

`async_api` и функциональные тесты используют Python 3.10, ETL — Python 3.12.

## Структура проекта

```text
movies_async_api/
├── async_api/                 # FastAPI-сервис
│   ├── src/
│   │   ├── api/               # endpoints, схемы ответов и DI
│   │   ├── cache/             # интерфейс кеша и Redis-реализация
│   │   ├── core/              # настройки и логирование
│   │   ├── db/                # клиенты Redis и Elasticsearch с retry-настройками
│   │   ├── models/            # внутренние Pydantic-модели
│   │   ├── repositories/      # интерфейсы и Elasticsearch-репозитории
│   │   ├── services/          # бизнес-логика
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── etl/
│   ├── postgres_to_es/
│   │   ├── interfaces/        # контракты source, loader, retry и connection
│   │   ├── loaders/           # загрузка документов в Elasticsearch
│   │   ├── models/            # исходные и целевые модели
│   │   ├── pipelines/         # films, genres и persons pipelines
│   │   ├── sources/           # чтение PostgreSQL
│   │   ├── state/             # состояние пайплайнов в Redis
│   │   ├── transforms/        # преобразование моделей
│   │   ├── backoff.py
│   │   ├── bootstrap.py
│   │   ├── config.py
│   │   ├── main.py
│   │   └── service.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── schemas/                   # JSON-схемы индексов Elasticsearch
├── tests/
│   ├── functional/
│   │   ├── fixtures/          # общие и предметные pytest-фикстуры
│   │   ├── src/               # тесты, разделённые по endpoint
│   │   ├── testdata/          # документы films, genres и persons
│   │   └── utils/             # вспомогательные функции ожидания и проверок
│   └── README.md
├── database_dump.sql
├── docker-compose.yml
├── mypy.ini
└── README.md
```

Подробная документация:

- [Async API](async_api/README.md)
- [ETL service](etl/README.md)
- [Functional tests](tests/README.md)

## Отказоустойчивость

В проекте используются два подхода к повторным попыткам:

- ETL применяет собственные `BackoffPolicy`, `BackoffRetryExecutor` и `@retryable` для PostgreSQL, Elasticsearch и Redis state;
- Async API использует retry-механизмы клиентских библиотек на транспортном уровне.

В Async API:

- Elasticsearch повторяет ошибки соединения, таймауты и настроенные HTTP-статусы с exponential backoff и jitter;
- Redis использует `Retry` вместе с `ExponentialWithJitterBackoff` для ошибок соединения и таймаутов.

Параметры количества повторов и задержек задаются в `async_api/.env` и передаются клиентам при их инициализации.

## Быстрый запуск

### 1. Создать файлы окружения

```bash
cp async_api/.env.example async_api/.env
cp etl/.env.example etl/.env
```

Для локального Docker Compose пароль PostgreSQL в `etl/.env` должен совпадать со значением из корневого `docker-compose.yml`:

```env
POSTGRES_PASSWORD=secret
```

### 2. Запустить проект

```bash
docker compose up --build
```

При первом запуске:

1. PostgreSQL загружает `database_dump.sql`;
2. ETL создаёт индексы `movies`, `genres` и `persons`;
3. ETL переносит данные в Elasticsearch;
4. Async API становится доступен на `http://localhost:8000`.

После смены major-версии Elasticsearch рекомендуется чистый запуск:

```bash
docker compose down -v
docker compose up --build
```

Команда `down -v` удаляет volumes PostgreSQL, Elasticsearch и Redis, поэтому все локальные данные будут созданы заново.

### 3. Проверить сервисы

Swagger UI:

```text
http://localhost:8000/api/openapi
```

OpenAPI JSON:

```text
http://localhost:8000/api/openapi.json
```

Elasticsearch:

```bash
curl "http://localhost:9200"
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/movies/_count?pretty"
curl "http://localhost:9200/genres/_count?pretty"
curl "http://localhost:9200/persons/_count?pretty"
```

### 4. Остановить проект

Сохранить данные в Docker volumes:

```bash
docker compose down
```

Удалить контейнеры вместе с данными PostgreSQL, Elasticsearch и Redis:

```bash
docker compose down -v
```

## API

Базовый префикс: `/api/v1`.

| Метод | URL | Назначение |
| --- | --- | --- |
| `GET` | `/films/` | Список фильмов, сортировка и фильтр по жанру |
| `GET` | `/films/search` | Полнотекстовый поиск фильмов |
| `GET` | `/films/{film_id}` | Фильм по UUID |
| `GET` | `/films/{film_id}/similar` | Похожие фильмы |
| `GET` | `/genres/` | Список и поиск жанров |
| `GET` | `/genres/{genre_id}` | Жанр по UUID |
| `GET` | `/persons/search` | Список и поиск персон |
| `GET` | `/persons/{person_id}` | Персона по UUID |
| `GET` | `/persons/{person_id}/films` | Фильмы персоны |

## Проверка типов

Из корня проекта:

```bash
mypy async_api/src etl/postgres_to_es
```

## Maintainability Index

Проверка выполняется из корня проекта:

```bash
radon mi async_api/src -s
radon mi etl/postgres_to_es -s
radon mi tests/functional -s
```

На текущем состоянии все проверенные Python-модули имеют категорию `A`.

| Компонент | Минимальное значение MI | Модуль |
| --- | ---: | --- |
| Async API | `55.89` | `async_api/src/api/v1/schemas/films.py` |
| ETL | `32.72` | `etl/postgres_to_es/sources/postgres.py` |
| Functional tests | `26.33` | `tests/functional/src/films/test_film_similar.py` |

Низкие значения отдельных тестовых файлов связаны главным образом с большим количеством сценариев, параметризаций и проверок внутри одного endpoint-модуля. Тесты при этом уже разделены по ресурсам и endpoint, а дальнейшее дробление ухудшило бы навигацию без заметной архитектурной пользы.
