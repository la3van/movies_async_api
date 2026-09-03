# Content Service

Асинхронный read-only HTTP API для фильмов, жанров и персон.

Сервис читает подготовленные документы из Elasticsearch и кеширует ответы в Redis. Исходная PostgreSQL-база напрямую Content Service не используется: её данные предварительно синхронизирует Content ETL.

В актуальной системе сервис называется `content-service`, доступен через
Nginx и дополнительно проверяет права через `auth-service`. `ugc-service`
обращается к нему для проверки существования фильма. Docker-образ по
умолчанию использует Python 3.10; CI собирает тестовое окружение также на
Python 3.11 и 3.12 через аргумент `PYTHON_VERSION`.

## Стек

- Python 3.10;
- FastAPI;
- Uvicorn;
- `elasticsearch[async]`;
- `redis.asyncio`;
- Pydantic v2;
- ORJSONResponse;
- OpenTelemetry SDK и OTLP/gRPC exporter;
- Jaeger.

## Архитектура

```text
Nginx
    ↓
HTTP endpoint
    ↓
Service
    ├── Cache interface
    │      ↑
    │   RedisCache
    └── Repository interface
           ↑
      Elasticsearch repository

Service ── OTLP/gRPC ──► Jaeger
```

## Структура

```text
content_service/
├── src/
│   ├── api/                  # endpoints, DI, API-схемы и мапперы
│   ├── cache/                # интерфейс кеша и Redis-реализация
│   ├── core/                 # настройки, логирование и tracing
│   ├── db/                   # клиенты Redis и Elasticsearch
│   ├── models/               # внутренние Pydantic-модели
│   ├── repositories/
│   │   ├── interfaces/       # контракты репозиториев
│   │   └── elastic/          # Elasticsearch-реализации и query bodies
│   ├── services/             # бизнес-логика и cache keys
│   └── main.py               # создание FastAPI-приложения
├── tests/
├── .coveragerc
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

Конкретные реализации зависимостей собираются в `src/api/dependencies.py`.

## Конфигурация

Из каталога `services/content_service`:

```bash
cp .env.example .env
```

Основные настройки:

```env
PROJECT_NAME=movies-content-service

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

# Cache TTL
FILM_CACHE_EXPIRE_IN_SECONDS=300
GENRE_CACHE_EXPIRE_IN_SECONDS=300
PERSON_CACHE_EXPIRE_IN_SECONDS=300
```

Настройки сортировки должны соответствовать полям Elasticsearch mappings из [`../../infrastructure/elasticsearch/mappings`](../../infrastructure/elasticsearch/mappings).

Количество retries задаётся после первоначальной попытки. Например, `ELASTIC_MAX_RETRIES=2` допускает максимум три обращения.

## Retries и exponential backoff

Повторные попытки являются ответственностью транспортных клиентов.

### Elasticsearch

`AsyncElasticsearch` использует:

- `max_retries`;
- `retry_on_timeout`;
- `retry_on_status`;
- exponential backoff с jitter.

### Redis

Redis-клиент использует `Retry` и `ExponentialWithJitterBackoff` для ошибок соединения и таймаутов.

Репозитории, кеш и бизнес-сервисы не дублируют retry-логику.

## Распределённая трассировка

Трассировка настраивается в `src/core/tracing.py` и подключается в `src/main.py` до обработки запросов.

### Автоматические spans

| Instrumentor | Что отображается в Jaeger |
| --- | --- |
| `FastAPIInstrumentor` | серверный HTTP-span для endpoint |
| `RedisInstrumentor` | `GET`, `SET` и другие Redis-команды |
| `ElasticsearchInstrumentor` | Elasticsearch search/get-запросы |

### Ручные spans сервисного слоя

Декоратор `@trace_method(...)` создаёт дочерний span вокруг бизнес-метода:

```text
content.films.get_by_id
content.films.get_sorted
content.films.search
content.films.get_similar
content.genres.get_by_id
content.genres.get_many
content.persons.get_by_id
content.persons.get_many
content.persons.get_films
```

Декоратор поддерживает sync- и async-функции. В Content Service используются асинхронные wrappers, а Redis и Elasticsearch spans автоматически становятся дочерними текущего service-span.

Пример cache miss:

```text
GET /api/v1/films/
└── content.films.get_sorted
    ├── Redis GET
    ├── Elasticsearch search
    └── Redis SET
```

При повторе запроса с теми же параметрами обычно отображается cache hit:

```text
GET /api/v1/films/
└── content.films.get_sorted
    └── Redis GET
```

### Переменные OpenTelemetry

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=content-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST=x-request-id
```

`OTEL_ENABLED=false` отключает настройку provider и instrumentors. В локальной конфигурации sampler равен `ALWAYS_ON`, поэтому записывается каждый запрос.

Проверка:

```bash
curl -i \
  -H "X-Request-ID: content-trace-check-001" \
  "http://127.0.0.1:8000/api/v1/films/?page_number=1&page_size=5"
```

Откройте `http://127.0.0.1:16686/`, выберите `content-service` и найдите последний trace. На серверном span должен быть атрибут `http.request.header.x_request_id`.

Общие сведения и диагностика: [../../infrastructure/jaeger/README.md](../../infrastructure/jaeger/README.md).

## Запуск через Docker Compose

Для доступа с хоста через общую точку входа:

```bash
docker compose up --build nginx
```

Nginx запускает Content Service и остальные HTTP-сервисы, указанные в его `depends_on`.

Запуск только Content Service для внутренних проверок:

```bash
docker compose up --build content-service
```

В этом режиме сервис доступен контейнерам по адресу `content-service:8000`, но его порт не опубликован на хост.

Полное окружение, включая Content ETL:

```bash
docker compose up --build
```

Логи сервиса и reverse proxy:

```bash
docker compose logs -f content-service nginx
```

## Локальный запуск

Из каталога `services/content_service`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

В `.env` укажите адреса Elasticsearch и Redis, доступные с хоста, затем запустите:

```bash
PYTHONPATH=src uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

## Документация API

В корневом Compose Content Service доступен с хоста только через Nginx:

- Swagger UI: `http://127.0.0.1:8000/api/openapi`
- OpenAPI JSON: `http://127.0.0.1:8000/api/openapi.json`
- базовый API-префикс: `/api/v1`

Внутри Docker-сети сервис доступен по адресу `http://content-service:8000`.

## Endpoints

### Films

```text
GET /api/v1/films/
GET /api/v1/films/search
GET /api/v1/films/{film_id}
GET /api/v1/films/{film_id}/similar
```

Поддерживаются пагинация, сортировка по рейтингу, фильтрация по жанру и полнотекстовый поиск.

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

Поддерживаются поиск персон и получение связанных фильмов.

## Кеширование

Redis используется как cache-aside слой:

1. сервис строит cache key;
2. проверяет Redis;
3. при cache miss обращается к Elasticsearch;
4. сохраняет результат с TTL;
5. возвращает ответ клиенту.

Ключи формируются в `src/services/cache_keys/`. В корневом Compose Content Service использует Redis DB `1`.

## Жизненный цикл клиентов

FastAPI lifespan:

1. создаёт асинхронные клиенты Elasticsearch и Redis;
2. передаёт настройки timeout, retries и backoff;
3. предоставляет клиенты через DI;
4. корректно закрывает подключения при завершении приложения.

## Функциональные тесты

Тесты находятся в [`tests/functional`](tests/functional) и выполняют реальные HTTP-запросы к изолированному сервису.

Инструкции: [tests/README.md](tests/README.md).

На момент текущего рефакторинга зафиксировано `99%` покрытия кода Content Service.

## Проверка типов

Из корня репозитория:

```bash
mypy services/content_service/src
```

## Maintainability Index

```bash
radon mi services/content_service/src -s
```

Актуальные результаты проекта хранятся в [`../../docs/CODE_MAINTAINABILITY.md`](../../docs/CODE_MAINTAINABILITY.md).