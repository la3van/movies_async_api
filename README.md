# Movies Backend

Backend онлайн-кинотеатра, оформленный как монорепозиторий из независимых сервисов.

Проект предоставляет:

- read-only API для фильмов, жанров и персон;
- сервис аутентификации и авторизации;
- инкрементальную синхронизацию данных PostgreSQL → Elasticsearch;
- кеширование ответов и хранение состояния ETL в Redis;
- изолированные функциональные тесты сервисов.

## Архитектура

```text
                         ┌────────────────────┐
                         │    HTTP clients    │
                         └─────────┬──────────┘
                                   │
                  ┌────────────────┴────────────────┐
                  │                                 │
                  ▼                                 ▼
        ┌───────────────────┐             ┌───────────────────┐
        │  Content Service  │             │   Auth Service    │
        │ films / genres /  │             │ users / roles /   │
        │ persons           │             │ permissions       │
        └─────────┬─────────┘             └─────────┬─────────┘
                  │                                 │
          ┌───────┴───────┐                 ┌───────┴───────┐
          ▼               ▼                 ▼               ▼
   Elasticsearch     Redis DB 1       PostgreSQL       Redis DB 2
          ▲                              auth
          │
   ┌──────┴─────────┐
   │  Content ETL   │──────────────► Redis DB 0
   └──────┬─────────┘                pipeline state
          │
          ▼
    PostgreSQL theatre
```

## Компоненты

| Компонент | Назначение |
| --- | --- |
| `content-service` | Read-only FastAPI API для фильмов, жанров и персон |
| `auth-service` | Аутентификация, авторизация, роли и permissions |
| `content-etl` | Инкрементальный перенос данных PostgreSQL → Elasticsearch |
| `theatre-db` | Исходная PostgreSQL-база контента |
| `auth-postgres` | Отдельная PostgreSQL-база Auth Service |
| `elasticsearch` | Read-модель и полнотекстовый поиск |
| `redis` | Состояние ETL и кеши сервисов |

## Структура репозитория

```text
./
├── docs/
│   └── CODE_MAINTAINABILITY.md
├── infrastructure/
│   ├── elasticsearch/
│   │   ├── mappings/
│   │   │   ├── genres.json
│   │   │   ├── movies.json
│   │   │   └── persons.json
│   │   └── README.md
│   ├── postgres/
│   │   ├── theatre/
│   │   │   └── init/
│   │   │       └── 0001_content_dump.sql
│   │   └── README.md
│   └── README.md
├── services/
│   ├── auth_service/
│   │   ├── alembic/
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   ├── content_etl/
│   │   ├── postgres_to_es/
│   │   └── README.md
│   ├── content_service/
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   └── README.md
├── docker-compose.yml
├── mypy.ini
└── README.md
```

Подробная документация:

- [Сервисы](services/README.md)
- [Content Service](services/content_service/README.md)
- [Функциональные тесты Content Service](services/content_service/tests/README.md)
- [Auth Service](services/auth_service/README.md)
- [Функциональные тесты Auth Service](services/auth_service/tests/README.md)
- [Content ETL](services/content_etl/README.md)
- [Инфраструктура](infrastructure/README.md)
- [Elasticsearch](infrastructure/elasticsearch/README.md)
- [PostgreSQL](infrastructure/postgres/README.md)
- [Поддерживаемость кода](docs/CODE_MAINTAINABILITY.md)

## Основные возможности

### Content Service

- получение фильмов, жанров и персон по UUID;
- пагинация и сортировка списков;
- фильтрация фильмов по жанру;
- полнотекстовый поиск;
- поиск похожих фильмов;
- получение фильмов, связанных с персоной;
- кеширование ответов в Redis;
- retry и exponential backoff на уровне клиентов Redis и Elasticsearch.

### Auth Service

- регистрация и вход пользователей;
- access JWT и refresh-token rotation;
- logout текущей и остальных сессий;
- управление профилем и паролем;
- история входов;
- роли и permissions;
- кеширование read-запросов в Redis;
- миграции PostgreSQL через Alembic.

### Content ETL

- независимые pipelines для фильмов, жанров и персон;
- пакетная инкрементальная загрузка;
- хранение курсоров в Redis;
- создание индексов по Elasticsearch mappings;
- exponential backoff для PostgreSQL, Elasticsearch и Redis.

## Технологии

- Python 3.10 и 3.12;
- FastAPI и Uvicorn;
- PostgreSQL 16;
- Elasticsearch 9.4.2;
- Redis 7;
- SQLAlchemy 2.0 и asyncpg;
- psycopg2;
- Pydantic v2;
- Alembic;
- pytest, pytest-asyncio, aiohttp и coverage.py;
- Docker Compose;
- mypy и Radon.

## Быстрый запуск

### 1. Подготовить окружение

Из корня репозитория:

```bash
cp services/content_service/.env.example services/content_service/.env
cp services/content_etl/.env.example services/content_etl/.env
cp services/auth_service/.env.example services/auth_service/.env
```

Пароли и имена баз в `.env` должны соответствовать значениям корневого `docker-compose.yml`.

### 2. Запустить проект

```bash
docker compose up --build
```

Запуск в фоне:

```bash
docker compose up -d --build
```

Проверить состояние контейнеров:

```bash
docker compose ps
```

Посмотреть логи приложений:

```bash
docker compose logs -f content-service content-etl auth-service
```

### 3. Проверить сервисы

Content Service:

- Swagger UI: `http://localhost:8000/api/openapi`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`

Auth Service:

- Swagger UI: `http://localhost:8008/docs`
- OpenAPI JSON: `http://localhost:8008/openapi.json`
- Healthcheck: `http://localhost:8008/health`

Elasticsearch:

```bash
curl "http://localhost:9200"
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/movies/_count?pretty"
curl "http://localhost:9200/genres/_count?pretty"
curl "http://localhost:9200/persons/_count?pretty"
```

## Запуск отдельных компонентов

```bash
docker compose up --build content-service
docker compose up --build auth-service
docker compose up --build content-etl
```

Compose автоматически поднимет зависимости, указанные в `depends_on`.

## Остановка и очистка

Остановить контейнеры с сохранением данных:

```bash
docker compose down
```

Полностью пересоздать локальное окружение:

```bash
docker compose down -v
docker compose up --build
```

`down -v` удаляет named volumes PostgreSQL, Elasticsearch и Redis. Используйте эту команду только тогда, когда локальные данные можно удалить.

## Функциональные тесты

Content Service:

```bash
cd services/content_service/tests/functional
docker compose up --build --abort-on-container-exit --exit-code-from tests tests
```

Auth Service:

```bash
cd services/auth_service/tests/functional
docker compose up --build --abort-on-container-exit --exit-code-from tests tests
```

Подробные команды запуска, coverage и очистки описаны в README соответствующих тестов.

## Проверка типов

Content Service и Content ETL из корня репозитория:

```bash
mypy services/content_service/src services/content_etl/postgres_to_es
```

Auth Service рекомендуется проверять из каталога самого сервиса:

```bash
cd services/auth_service
mypy src
```

Так исключается неоднозначность одинаково названных верхнеуровневых пакетов разных сервисов.
