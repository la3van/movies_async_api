# Async API

Асинхронный read-only HTTP API для работы с фильмами, жанрами и персонами. Сервис читает данные из Elasticsearch и кеширует результаты в Redis.

## Стек

- Python 3.10;
- FastAPI;
- Uvicorn;
- `elasticsearch[async]` 9.4.1;
- `redis.asyncio` из redis-py 7.1.0;
- Pydantic v2;
- ORJSONResponse.

Elasticsearch-сервер в основном и тестовом Docker Compose использует версию 9.4.2.

## Архитектура

```text
HTTP endpoint
    ↓
Service
    ├── Cache interface
    │      ↑
    │   RedisCache
    └── Repository interface
           ↑
      Elasticsearch repository
```

Сервис организован по слоям:

| Каталог | Назначение |
| --- | --- |
| `src/api/` | FastAPI endpoints, DI, схемы ответов и мапперы |
| `src/services/` | Бизнес-логика и формирование cache keys |
| `src/repositories/interfaces/` | Контракты репозиториев |
| `src/repositories/elastic/` | Реализации репозиториев и тела запросов Elasticsearch |
| `src/cache/` | Абстракция кеша и реализация Redis |
| `src/models/` | Внутренние Pydantic-модели |
| `src/db/` | Инициализация, retry-настройки и закрытие внешних клиентов |
| `src/core/` | Настройки и конфигурация логирования |
| `src/main.py` | Создание FastAPI-приложения |

Конкретные зависимости собираются в `src/api/dependencies.py`.

## Конфигурация

Создайте файл окружения:

```bash
cp .env.example .env
```

Основные переменные:

```env
PROJECT_NAME=movies-async-api

# Elasticsearch
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_REQUEST_TIMEOUT=30
ELASTIC_MOVIES_INDEX=movies
ELASTIC_GENRES_INDEX=genres
ELASTIC_PERSONS_INDEX=persons

ELASTIC_MAX_RETRIES=2
ELASTIC_RETRY_ON_TIMEOUT=true
ELASTIC_RETRY_ON_STATUS='[429, 502, 503, 504]'
ELASTIC_RETRY_BACKOFF_BASE=0.1
ELASTIC_RETRY_BACKOFF_CAP=1.0

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

REDIS_MAX_RETRIES=2
REDIS_RETRY_BACKOFF_BASE=0.1
REDIS_RETRY_BACKOFF_CAP=1.0

# Services
FILM_SORT_FIELDS='{"imdb_rating":"imdb_rating"}'
GENRE_SORT_FIELDS='{"name":"name.raw"}'
PERSON_SORT_FIELDS='{"full_name":"full_name.raw"}'

FILM_CACHE_EXPIRE_IN_SECONDS=300
GENRE_CACHE_EXPIRE_IN_SECONDS=300
PERSON_CACHE_EXPIRE_IN_SECONDS=300
```

Точные значения sort fields должны соответствовать mappings из каталога `schemas/`.

`ELASTIC_MAX_RETRIES` и `REDIS_MAX_RETRIES` задают количество повторов после первоначальной попытки. Например, значение `2` означает максимум три обращения к внешнему сервису.

## Retries и exponential backoff

Async API не содержит отдельного retry-декоратора или собственного executor. Повторные попытки настраиваются при создании клиентов в `src/db/elastic.py` и `src/db/redis.py`.

### Elasticsearch

`AsyncElasticsearch` использует:

- `max_retries` — максимальное количество повторов;
- `retry_on_timeout` — повтор запроса при клиентском таймауте;
- `retry_on_status` — HTTP-статусы, при которых разрешён повтор;
- `retry_backoff_base` и `retry_backoff_cap` — exponential backoff с jitter.

Ошибки соединения повторяются автоматически, если retries включены. По умолчанию в конфигурации проекта повторяются статусы `429`, `502`, `503` и `504`.

### Redis

Redis-клиент использует `Retry` и `ExponentialWithJitterBackoff`. Повторяются ошибки соединения и таймауты, а начальная и максимальная задержки задаются через настройки приложения.

Backoff остаётся транспортной ответственностью клиентов. `RedisCache`, сервисы и Elasticsearch-репозитории не содержат собственной логики повторов.

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up --build async_api
```

Обычно API запускается вместе с PostgreSQL, Elasticsearch, Redis и ETL:

```bash
docker compose up --build
```

После перехода с Elasticsearch 8 на Elasticsearch 9 выполните чистый запуск:

```bash
docker compose down -v
docker compose up --build
```

`down -v` удаляет все volumes корневого Compose-проекта, включая PostgreSQL и Redis.

## Локальный запуск

Из каталога `async_api`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Для локального запуска в `.env` укажите доступные с хоста адреса Elasticsearch и Redis, например `localhost`.

```bash
PYTHONPATH=src uvicorn src.main:app   --host 0.0.0.0   --port 8000   --reload
```

Docker-образ использует тот же entry point без `--reload`.

## Документация API

- Swagger UI: `http://localhost:8000/api/openapi`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

Базовый API-префикс: `/api/v1`.

## Endpoints

### Films

```text
GET /api/v1/films/
GET /api/v1/films/search
GET /api/v1/films/{film_id}
GET /api/v1/films/{film_id}/similar
```

Поддерживаются пагинация, сортировка по `imdb_rating`, фильтрация по UUID жанра и полнотекстовый поиск по названию, описанию и именам участников.

### Genres

```text
GET /api/v1/genres/
GET /api/v1/genres/{genre_id}
```

Список поддерживает поиск, пагинацию и сортировку по имени.

### Persons

```text
GET /api/v1/persons/search
GET /api/v1/persons/{person_id}
GET /api/v1/persons/{person_id}/films
```

Поддерживаются поиск и сортировка персон, а также получение связанных фильмов.

## Кеширование

Redis хранит ответы API с TTL, заданным отдельно для фильмов, жанров и персон.

Ключи формируются в `src/services/cache_keys/`. Сервис сначала проверяет кеш, затем обращается к репозиторию и сохраняет полученный результат.

В основном Docker Compose для кеша используется Redis DB `1`.

## Жизненный цикл клиентов

FastAPI lifespan:

1. создаёт `AsyncElasticsearch` и `Redis` при старте;
2. передаёт им параметры timeout, retries и backoff из `Settings`;
3. предоставляет клиентов через зависимости;
4. закрывает подключения при завершении приложения.

## Проверка типов

Из корня проекта:

```bash
mypy async_api/src
```

## Maintainability Index

Проверка выполняется из корня проекта:

```bash
radon mi async_api/src -s
```

Все модули Async API имеют категорию `A`. Текущие значения для наиболее объёмных модулей:

| Модуль | MI |
| --- | ---: |
| `src/api/v1/schemas/films.py` | `55.89` |
| `src/cache/redis.py` | `57.52` |
| `src/repositories/elastic/bodies/persons.py` | `58.97` |
| `src/services/film.py` | `60.57` |
| `src/db/redis.py` | `60.77` |
| `src/repositories/elastic/bodies/films.py` | `61.63` |
| `src/db/elastic.py` | `61.98` |
| `src/services/person.py` | `62.51` |
| `src/repositories/elastic/bodies/genres.py` | `64.28` |
| `src/models/film.py` | `69.39` |
| `src/services/genre.py` | `68.47` |
| `src/api/v1/endpoints/persons.py` | `73.31` |
| `src/api/v1/endpoints/films.py` | `74.19` |
| `src/api/v1/endpoints/genres.py` | `80.95` |
| `src/services/cache_keys/films.py` | `88.41` |
| `src/models/genre.py` | `94.30` |

Остальные проверенные модули имеют MI `100.00`.

## Функциональные тесты

Тесты находятся в `tests/functional` и запускаются в отдельном Docker Compose окружении. Они разделены по ресурсам и endpoint, а общие фикстуры вынесены в `tests/functional/fixtures`.

Инструкции: [tests/README.md](../tests/README.md).
