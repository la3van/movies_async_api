# Services

Каталог содержит независимо запускаемые приложения монорепозитория.

## Состав

```text
services/
├── auth_service/
├── content_etl/
├── content_service/
└── README.md
```

| Каталог | Docker Compose service | Назначение |
| --- | --- | --- |
| [`content_service`](content_service) | `content-service` | Read-only HTTP API контента |
| [`auth_service`](auth_service) | `auth-service` | Аутентификация, авторизация и пользователи |
| [`content_etl`](content_etl) | `content-etl` | Синхронизация контента PostgreSQL → Elasticsearch |

## Принципы организации

Каждый сервис хранит собственные:

- исходный код;
- зависимости;
- Dockerfile;
- `.env.example`;
- README;
- тесты, если они относятся только к этому сервису.

Корневой каталог `services/` — это уровень приложений монорепозитория. Каталоги `src/services/` внутри FastAPI-приложений имеют другой смысл и содержат слой бизнес-логики.

Общие для нескольких приложений инфраструктурные ресурсы не находятся внутри конкретного сервиса. Они вынесены в [`../infrastructure`](../infrastructure).

## Content Service

Read-only API фильмов, жанров и персон.

```text
content_service/
├── src/
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

Документация: [content_service/README.md](content_service/README.md).

## Auth Service

Сервис пользователей, JWT-аутентификации, refresh-сессий, ролей и permissions.

```text
auth_service/
├── alembic/
├── src/
├── tests/
├── Dockerfile
├── requirements.txt
└── README.md
```

Документация: [auth_service/README.md](auth_service/README.md).

## Content ETL

Фоновый процесс без HTTP API. Читает контентную PostgreSQL-базу и синхронизирует Elasticsearch.

```text
content_etl/
├── postgres_to_es/
├── Dockerfile
├── requirements.txt
└── README.md
```

Документация: [content_etl/README.md](content_etl/README.md).

## Запуск

Все сервисы:

```bash
docker compose up --build
```

Отдельный сервис из корня репозитория:

```bash
docker compose up --build content-service
docker compose up --build auth-service
docker compose up --build content-etl
```

Для просмотра логов:

```bash
docker compose logs -f content-service
docker compose logs -f auth-service
docker compose logs -f content-etl
```
