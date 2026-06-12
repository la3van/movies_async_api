# Movies Async API

Read-only API для онлайн-кинотеатра.

Проект состоит из FastAPI-сервиса для получения данных о фильмах, жанрах и персонах, а также ETL-сервиса, который переносит данные из PostgreSQL в Elasticsearch.

## 1. Краткое описание проекта

Проект реализует backend для онлайн-кинотеатра.

Основная идея:

```text
PostgreSQL
   ↓
ETL service
   ↓
Elasticsearch
   ↓
FastAPI
   ↓
Client
```

PostgreSQL хранит исходные данные. ETL-сервис читает данные из PostgreSQL, преобразует их в документы Elasticsearch и загружает в индексы. Elasticsearch используется как read-модель для быстрых поисковых запросов. FastAPI предоставляет read-only API для клиентов. Redis используется для хранения состояния ETL и кеширования ответов API.

Основные Docker Compose сервисы:

| Сервис          | Назначение                            |
| --------------- | ------------------------------------- |
| `async_api`     | FastAPI-приложение                    |
| `etl`           | ETL-сервис PostgreSQL → Elasticsearch |
| `theatre-db`    | PostgreSQL с исходными данными        |
| `elasticsearch` | Поисковый движок и read-хранилище     |
| `redis`         | Хранилище состояния ETL и кеш API     |

Индексы Elasticsearch:

| Индекс    | Содержимое |
| --------- | ---------- |
| `movies`  | Фильмы     |
| `genres`  | Жанры      |
| `persons` | Персоны    |

Redis используется так:

| Redis DB | Назначение    |
| -------- | ------------- |
| `0`      | Состояние ETL |
| `1`      | Кеш FastAPI   |

## 2. Стек технологий

* Python 3.12
* FastAPI
* Uvicorn
* PostgreSQL 16
* Elasticsearch 8.6.2
* Redis 7
* Docker Compose
* Pydantic v2
* pydantic-settings
* ORJSONResponse

## 3. Структура проекта

```text
movies_async_api/
├── async_api/
│   ├── src/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── films.py
│   │   │       ├── genres.py
│   │   │       └── persons.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logger.py
│   │   ├── db/
│   │   │   ├── elastic.py
│   │   │   └── redis.py
│   │   ├── models/
│   │   │   ├── film.py
│   │   │   ├── genre.py
│   │   │   └── person.py
│   │   ├── services/
│   │   │   ├── film.py
│   │   │   ├── genre.py
│   │   │   └── person.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── etl/
│   ├── postgres_to_es/
│   │   ├── models/
│   │   │   ├── common.py
│   │   │   ├── film.py
│   │   │   ├── genre.py
│   │   │   ├── movies.py
│   │   │   └── person.py
│   │   ├── pipelines/
│   │   │   ├── base.py
│   │   │   ├── films.py
│   │   │   ├── genres.py
│   │   │   └── persons.py
│   │   ├── schemas/
│   │   │   ├── movies_schema.json
│   │   │   ├── genres_schema.json
│   │   │   └── persons_schema.json
│   │   ├── transforms/
│   │   │   ├── movies.py
│   │   │   ├── genres.py
│   │   │   └── persons.py
│   │   ├── backoff.py
│   │   ├── config.py
│   │   ├── elastic.py
│   │   ├── main.py
│   │   ├── postgres.py
│   │   ├── service.py
│   │   └── state.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
│
├── tests/
├── database_dump.sql
├── docker-compose.yml
├── .gitignore
└── README.md
```

### `async_api`

FastAPI-приложение.

Основные модули:

| Модуль               | Назначение                                      |
| -------------------- | ----------------------------------------------- |
| `api/v1/films.py`    | HTTP-ручки для фильмов                          |
| `api/v1/genres.py`   | HTTP-ручки для жанров                           |
| `api/v1/persons.py`  | HTTP-ручки для персон                           |
| `services/film.py`   | Логика работы с фильмами, Elasticsearch и Redis |
| `services/genre.py`  | Логика работы с жанрами                         |
| `services/person.py` | Логика работы с персонами                       |
| `models/`            | Pydantic-модели API                             |
| `db/elastic.py`      | Инициализация AsyncElasticsearch                |
| `db/redis.py`        | Инициализация Redis-клиента                     |
| `core/config.py`     | Настройки приложения                            |
| `main.py`            | Точка входа FastAPI-приложения                  |

### `etl`

ETL-сервис для переноса данных из PostgreSQL в Elasticsearch.

Основные модули:

| Модуль        | Назначение                                                   |
| ------------- | ------------------------------------------------------------ |
| `postgres.py` | Извлечение данных из PostgreSQL                              |
| `elastic.py`  | Создание индексов и bulk-загрузка документов в Elasticsearch |
| `state.py`    | Хранение состояния ETL в Redis                               |
| `backoff.py`  | Повторные попытки при временных ошибках                      |
| `service.py`  | Оркестратор ETL-пайплайнов                                   |
| `main.py`     | Точка входа ETL-сервиса                                      |
| `models/`     | Модели PostgreSQL и Elasticsearch-документов                 |
| `pipelines/`  | Отдельные пайплайны загрузки индексов                        |
| `transforms/` | Преобразование PostgreSQL-моделей в Elasticsearch-документы  |
| `schemas/`    | Схемы индексов Elasticsearch                                 |

Пайплайны:

| Пайплайн          | Назначение                                 |
| ----------------- | ------------------------------------------ |
| `MoviesPipeline`  | Загружает данные фильмов в индекс `movies` |
| `GenresPipeline`  | Загружает жанры в индекс `genres`          |
| `PersonsPipeline` | Загружает персоны в индекс `persons`       |

## 4. API endpoints

| Метод | URL                                | Описание                   |
| ----- | ---------------------------------- | -------------------------- |
| `GET` | `/api/v1/films/`                   | Список фильмов             |
| `GET` | `/api/v1/films/search`             | Поиск фильмов              |
| `GET` | `/api/v1/films/{film_id}`          | Полная информация о фильме |
| `GET` | `/api/v1/films/{film_id}/similar`  | Похожие фильмы             |
| `GET` | `/api/v1/genres/`                  | Список жанров              |
| `GET` | `/api/v1/genres/{genre_id}`        | Информация о жанре         |
| `GET` | `/api/v1/persons/search`           | Поиск персон               |
| `GET` | `/api/v1/persons/{person_id}`      | Информация о персоне       |
| `GET` | `/api/v1/persons/{person_id}/film` | Фильмы персоны             |

Swagger UI:

```text
http://localhost:8000/api/openapi
```

OpenAPI JSON:

```text
http://localhost:8000/api/openapi.json
```

## 5. Запуск проекта

### 5.1. Подготовить `.env` файлы

В проекте используются два `.env` файла:

```text
async_api/.env
etl/.env
```

Их можно создать из примеров:

```bash
cp async_api/.env.example async_api/.env
cp etl/.env.example etl/.env
```

Пример `async_api/.env`:

```env
PROJECT_NAME=Read-only API для онлайн кинотеатра

ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_REQUEST_TIMEOUT=30

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
```

Пример `etl/.env`:

```env
# PostgreSQL
POSTGRES_HOST=theatre-db
POSTGRES_PORT=5432
POSTGRES_DB=theatre
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secret
POSTGRES_OPTIONS="-c search_path=public,content"
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_STATEMENT_TIMEOUT_MS=30000

# Elasticsearch
ELASTIC_HOST=elasticsearch
ELASTIC_PORT=9200
ELASTIC_REQUEST_TIMEOUT=30
MOVIES_INDEX=movies
GENRES_INDEX=genres
PERSONS_INDEX=persons

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_STATE_KEY_PREFIX=etl_state
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5

# ETL
BATCH_SIZE=100
ETL_SLEEP_TIME=1

# Backoff
BACKOFF_START_SLEEP_TIME=0.1
BACKOFF_FACTOR=2
BACKOFF_BORDER_SLEEP_TIME=10
BACKOFF_JITTER=True
```

### 5.2. Запустить проект

Собрать и запустить все сервисы:

```bash
docker compose up --build -d
```

Посмотреть статусы контейнеров:

```bash
docker compose ps -a
```

Ожидаемое состояние:

```text
async_api       Up
elasticsearch   Up healthy
redis           Up healthy
theatre-db      Up healthy
etl             Up
```

### 5.4. Остановить проект

Остановить контейнеры без удаления данных:

```bash
docker compose down
```

Остановить контейнеры и удалить volumes:

```bash
docker compose down -v
```

Команда `docker compose down -v` удалит данные PostgreSQL, Elasticsearch и Redis. После следующего запуска PostgreSQL заново инициализируется из `database_dump.sql`, а ETL заново создаст индексы и заполнит Elasticsearch.

## 6. Проверка проекта через терминал

### 6.1. Проверить контейнеры

```bash
docker compose ps -a
```

### 6.2. Смотреть логи API

```bash
docker compose logs --tail=200 async_api
```

Следить за логами API в реальном времени:

```bash
docker compose logs -f async_api
```

### 6.3. Смотреть логи ETL

```bash
docker compose logs --tail=200 etl
```

Следить за логами ETL в реальном времени:

```bash
docker compose logs -f etl
```

### 6.4. Проверить Swagger

```bash
curl -I "http://localhost:8000/api/openapi"
```

Ожидаемый результат:

```text
HTTP/1.1 200 OK
```

Проверить OpenAPI JSON:

```bash
curl "http://localhost:8000/api/openapi.json"
```

### 6.5. Проверить индексы Elasticsearch

Список индексов:

```bash
curl "http://localhost:9200/_cat/indices?v"
```

Ожидаемые индексы:

```text
movies
genres
persons
```

Количество документов в индексах:

```bash
curl "http://localhost:9200/movies/_count?pretty"
curl "http://localhost:9200/genres/_count?pretty"
curl "http://localhost:9200/persons/_count?pretty"
```

Посмотреть один документ из индекса `movies`:

```bash
curl "http://localhost:9200/movies/_search?size=1&pretty"
```

Посмотреть один документ из индекса `genres`:

```bash
curl "http://localhost:9200/genres/_search?size=1&pretty"
```

Посмотреть один документ из индекса `persons`:

```bash
curl "http://localhost:9200/persons/_search?size=1&pretty"
```

### 6.6. Проверить состояние ETL в Redis

Посмотреть ключи в Redis DB 0:

```bash
docker compose exec redis redis-cli -n 0 keys '*'
```

Пример ожидаемых ключей:

```text
etl_state:movies
etl_state:genres
etl_state:persons
```

Посмотреть состояние конкретного пайплайна:

```bash
docker compose exec redis redis-cli -n 0 get etl_state:movies
docker compose exec redis redis-cli -n 0 get etl_state:genres
docker compose exec redis redis-cli -n 0 get etl_state:persons
```

Если команда возвращает `(nil)`, значит такого ключа в Redis нет. Это может быть нормально, если пайплайн ещё не успел сохранить состояние или ключ называется иначе.

### 6.7. Проверить кеш API в Redis

Сначала выполнить запрос к API:

```bash
curl "http://localhost:8000/api/v1/films/?page_number=1&page_size=5"
```

Потом проверить ключи в Redis DB 1:

```bash
docker compose exec redis redis-cli -n 1 keys '*'
```

Пример ожидаемого ключа:

```text
films:sort=-imdb_rating:genre=all:page=1:size=5
```

### 6.8. Проверить API фильмов

Список фильмов:

```bash
curl "http://localhost:8000/api/v1/films/?page_number=1&page_size=5" | python -m json.tool
```

Поиск фильмов:

```bash
curl "http://localhost:8000/api/v1/films/search?query=star&page_number=1&page_size=5" | python -m json.tool
```

Получить фильм по UUID:

```bash
curl "http://localhost:8000/api/v1/films/2a090dde-f688-46fe-a9f4-b781a985275e" | python -m json.tool
```

Получить похожие фильмы:

```bash
curl "http://localhost:8000/api/v1/films/2a090dde-f688-46fe-a9f4-b781a985275e/similar?page_number=1&page_size=5" | python -m json.tool
```

### 6.9. Проверить API жанров

Список жанров:

```bash
curl "http://localhost:8000/api/v1/genres/?page_number=1&page_size=5" | python -m json.tool
```

Поиск жанров:

```bash
curl "http://localhost:8000/api/v1/genres/?query=action&page_number=1&page_size=5" | python -m json.tool
```

Получить жанр по UUID:

```bash
curl "http://localhost:8000/api/v1/genres/<genre_uuid>" | python -m json.tool
```

### 6.10. Проверить API персон

Поиск персон:

```bash
curl "http://localhost:8000/api/v1/persons/search?query=star&page_number=1&page_size=5" | python -m json.tool
```

Получить персону по UUID:

```bash
curl "http://localhost:8000/api/v1/persons/<person_uuid>" | python -m json.tool
```

Получить фильмы персоны:

```bash
curl "http://localhost:8000/api/v1/persons/<person_uuid>/film?page_number=1&page_size=5" | python -m json.tool
```

## 7. Полный сброс данных

Если нужно удалить старые индексы Elasticsearch, состояние Redis и данные PostgreSQL:

```bash
docker compose down -v
docker compose up --build -d
```

После этого:

* PostgreSQL заново инициализируется из `database_dump.sql`;
* Redis будет очищен;
* Elasticsearch будет пустым;
* ETL создаст индексы `movies`, `genres`, `persons`;
* ETL заново загрузит данные.

Если нужно удалить только индексы Elasticsearch:

```bash
curl -X DELETE "http://localhost:9200/movies,genres,persons"
```

После этого нужно перезапустить ETL или весь проект, чтобы индексы были созданы заново.

## 8. Кеширование

FastAPI использует Redis DB 1 для кеширования ответов API.

Примеры ключей кеша API:

```text
films:sort=-imdb_rating:genre=all:page=1:size=5
film:<uuid>
genres:...
persons:...
```

ETL использует Redis DB 0 для хранения состояния обработки.

Примеры ключей состояния ETL:

```text
etl_state:movies
etl_state:genres
etl_state:persons
```

## 9. Соответствие требованиям проекта

| Требование | Как реализовано |
|---|---|
| Структура API понятна пользователям и задокументирована | API описано через FastAPI/OpenAPI. Swagger доступен по адресу `/api/openapi`. Ручки разделены по сущностям: `films`, `genres`, `persons`. |
| Код проекта аккуратный и без дублирования | Проект разделён на два сервиса: `async_api` и `etl`.<br>В API логика разделена на `api`, `services`, `models`, `db`.<br>В ETL логика разделена на `pipelines`, `transforms`, `models`, `postgres`, `elastic`, `state`. |
| Время ответа сервиса не превышает 200 мс | Для быстрых ответов используются Elasticsearch как read-модель и Redis-кеш. Повторные запросы к API читаются из Redis. Для проверки время надо замерять на тестовых данных. |
| Решена проблема 10k соединений | API реализован на FastAPI с асинхронными клиентами Redis и Elasticsearch. Это позволяет эффективно обрабатывать большое количество I/O-запросов. Но реально протестировать на практике на данный момент это невозможно. |
| Объём данных: 200 000+ фильмов и 100+ жанров | Данные загружаются из PostgreSQL в Elasticsearch через ETL-сервис. Проверить количество документов можно через `_count` в индексах `movies` и `genres`. На данный момент сгружены только тестовые данные(около 30 жанров, 1000 фильмов и 4000 персон).|

## 10. TODO

* Реализовать автотесты для Elasticsearch:

  * проверка создания индексов;
  * проверка mappings;
  * проверка bulk-загрузки документов;
  * проверка поиска по индексам `movies`, `genres`, `persons`.

* Реализовать автотесты для ETL:

  * проверка чтения изменённых записей из PostgreSQL;
  * проверка сохранения состояния ETL в Redis;
  * проверка повторного запуска ETL с сохранённого курсора;
  * проверка трансформации PostgreSQL-моделей в Elasticsearch-документы.

* Подготовить Postman-коллекцию для ручного тестирования API:

  * список фильмов;
  * поиск фильмов;
  * получение фильма по UUID;
  * похожие фильмы;
  * список жанров;
  * получение жанра по UUID;
  * поиск персон;
  * получение персоны по UUID;
  * получение фильмов персоны.

* Добавить инструкцию по запуску Postman-коллекции.
