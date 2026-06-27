# Async API

Асинхронный read-only HTTP API для работы с фильмами, жанрами и персонами. Сервис читает данные из Elasticsearch и кеширует результаты в Redis.

## Стек

- Python 3.10;
- FastAPI;
- Uvicorn;
- `elasticsearch[async]`;
- `redis.asyncio`;
- Pydantic v2;
- ORJSONResponse.

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
| `src/db/` | Инициализация и закрытие внешних клиентов |
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
PROJECT_NAME=movies-async-API

ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_REQUEST_TIMEOUT=30

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

FILM_SORT_FIELDS='{"imdb_rating":"imdb_rating"}'
GENRE_SORT_FIELDS='{"name":"name.raw"}'
PERSON_SORT_FIELDS='{"full_name":"full_name.raw"}'

FILM_CACHE_EXPIRE_IN_SECONDS=300
GENRE_CACHE_EXPIRE_IN_SECONDS=300
PERSON_CACHE_EXPIRE_IN_SECONDS=300
```

Точные значения sort fields должны соответствовать mappings из каталога `schemas/`.

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up --build async_api
```

Обычно API запускается вместе с Elasticsearch, Redis и ETL:

```bash
docker compose up --build
```

## Локальный запуск

Из каталога `async_api`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Для локального запуска в `.env` укажите доступные с хоста адреса Elasticsearch и Redis, например `localhost`.

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
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

1. создаёт AsyncElasticsearch и Redis при старте;
2. предоставляет их через зависимости;
3. закрывает подключения при завершении приложения.

## Проверка типов

Из корня проекта:

```bash
mypy async_api/src
```

## Функциональные тесты

Тесты находятся в `tests/functional` и запускаются в отдельном Docker Compose окружении. Инструкции: [tests/README.md](../tests/README.md).
