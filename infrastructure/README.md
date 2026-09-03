# Infrastructure

Каталог содержит общие инфраструктурные артефакты проекта, которые не принадлежат одному конкретному приложению.

## Структура

```text
infrastructure/
├── clickhouse/
│   └── init.sql
├── elasticsearch/
│   ├── mappings/
│   │   ├── genres.json
│   │   ├── movies.json
│   │   └── persons.json
│   └── README.md
├── jaeger/
│   └── README.md
├── nginx/
│   ├── nginx.conf
│   └── README.md
├── postgres/
│   ├── theatre/
│   │   └── init/
│   │       └── 0001_content_dump.sql
│   └── README.md
└── README.md
```

## Elasticsearch

[`elasticsearch/mappings`](elasticsearch/mappings) содержит settings и mappings индексов:

- `movies`;
- `genres`;
- `persons`.

Их используют:

- Content ETL при создании индексов;
- функциональные тесты Content Service.

Подробнее: [elasticsearch/README.md](elasticsearch/README.md).

## Nginx

[`nginx/nginx.conf`](nginx/nginx.conf) настраивает единую точку входа для прикладных HTTP-сервисов на `127.0.0.1:8000`.

Основные маршруты:

- `/api/v1/films`, `/genres`, `/persons` и `/api/openapi*` → Content Service;
- `/api/v1/auth`, `/users`, `/roles`, `/permissions`, `/docs`, `/openapi.json` и `/health` → Auth Service;
- `/api/v1/events` → Events Service;
- `/api/v1/bookmarks`, `/ratings` и `/reviews` → UGC Service;
- `/ugc/docs`, `/ugc/openapi.json`, `/ugc/redoc`, `/ugc/health` и
  `/ugc/ready` → UGC Service;
- `/admin/`, `/static/` и `/__debug__/` → Admin Service.

Все прикладные HTTP-сервисы доступны с хоста только через Nginx. Собственные
порты приложений остаются внутри Docker-сети.

Подробнее: [nginx/README.md](nginx/README.md).

## Jaeger и OpenTelemetry

[`jaeger/README.md`](jaeger/README.md) описывает распределённую трассировку HTTP-сервисов.

Корневой Docker Compose запускает `jaegertracing/all-in-one`:

- OTLP/gRPC внутри Docker-сети: `jaeger:4317`;
- Jaeger UI на хосте: `http://127.0.0.1:16686/`.

Traces экспортируют `content-service`, `auth-service`, `admin-service`,
`events-service` и `ugc-service`. Nginx не создаёт OpenTelemetry spans, но
назначает `X-Request-ID`, который сохраняется в серверных spans и access log.

Подробнее: [jaeger/README.md](jaeger/README.md).

## PostgreSQL

[`postgres/theatre/init`](postgres/theatre/init) содержит SQL-инициализацию исходной базы контента.

SQL-файлы монтируются в `/docker-entrypoint-initdb.d` контейнера `theatre-db` и выполняются официальным образом PostgreSQL при первом создании пустого volume.

Подробнее: [postgres/README.md](postgres/README.md).

## Kafka, ClickHouse и MongoDB

Kafka хранит поток пользовательских событий между Events Service и Events
ETL. `clickhouse/init.sql` создаёт аналитическую таблицу для Events ETL.
MongoDB является основным хранилищем UGC Service и сохраняет данные в named
volume `mongodb_data`.

## Правила изменений

- инфраструктурные файлы не должны импортироваться как Python-пакеты;
- mappings должны меняться синхронно с ETL и запросами Content Service;
- SQL init-скрипты выполняются только при создании новой PostgreSQL data directory;
- маршруты Nginx должны меняться синхронно с публичными URL HTTP-сервисов;
- имена OpenTelemetry-сервисов и OTLP endpoint должны совпадать с Compose-конфигурацией;
- в span-атрибуты нельзя записывать пароли, JWT, refresh-токены и другие секреты;
- порядок SQL-скриптов задаётся числовым префиксом имени файла;
- секреты и локальные `.env` в этот каталог не добавляются.

## Повторная инициализация

Изменение init SQL не применяется к существующему PostgreSQL volume автоматически.

Полная очистка локального окружения:

```bash
docker compose down -v
docker compose up --build
```

Команда удаляет данные всех named volumes текущего Compose-проекта.