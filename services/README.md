# Services

Каталог содержит независимо запускаемые приложения монорепозитория онлайн-кинотеатра.

## Состав

```text
services/
├── admin_service/
├── auth_service/
├── content_etl/
├── content_service/
└── README.md
```

| Каталог | Docker Compose service | Назначение |
| --- | --- | --- |
| [`admin_service`](admin_service) | `admin-service` | Django Admin для управления контентом |
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

Корневой каталог `services/` — уровень независимо запускаемых приложений монорепозитория.

Каталоги `src/services/` внутри FastAPI-приложений имеют другой смысл и содержат слой бизнес-логики конкретного приложения.

Общие для нескольких приложений инфраструктурные ресурсы вынесены в [`../infrastructure`](../infrastructure).

## Admin Service

Django Admin для управления фильмами, жанрами и персонами.

```text
admin_service/
├── admin_auth/
├── admin_panel/
├── content/
├── Dockerfile
├── entrypoint.sh
├── manage.py
├── requirements.txt
└── README.md
```

Сервис:

- предоставляет интерфейс Django Admin;
- проверяет логин и пароль через `auth-service`;
- разрешает вход только активным суперпользователям;
- создаёт локального технического пользователя без рабочего пароля;
- хранит Django-сессии и журнал действий в SQLite;
- читает и изменяет существующие таблицы PostgreSQL в схеме `content`;
- не управляет структурой контентных таблиц через Django migrations;
- запускается через Gunicorn;
- отдаёт статические файлы через WhiteNoise;
- поддерживает опциональную Django Debug Toolbar.

Документация: [admin_service/README.md](admin_service/README.md).

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

Сервис читает данные из Elasticsearch и кеширует ответы в Redis.

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

Auth Service является источником истины для пользователей и паролей.

Admin Service использует его endpoints входа и получения текущего пользователя, но не хранит настоящий пароль администратора в своей SQLite-базе.

Документация: [auth_service/README.md](auth_service/README.md).

## Content ETL

Фоновый процесс без HTTP API.

```text
content_etl/
├── postgres_to_es/
├── Dockerfile
├── requirements.txt
└── README.md
```

Сервис читает контентную PostgreSQL-базу, преобразует фильмы, жанры и персон и синхронизирует документы Elasticsearch.

Состояние инкрементальных pipelines хранится в Redis.

Документация: [content_etl/README.md](content_etl/README.md).

## Связи сервисов

```text
Admin Service
├── HTTP       → Auth Service
├── PostgreSQL → theatre-db / schema content
└── SQLite     → служебные данные Django

Content ETL
├── PostgreSQL   → theatre-db
├── Redis DB 0   → pipeline state
└── Elasticsearch → movies / genres / persons

Content Service
├── Elasticsearch → read model
└── Redis DB 1    → response cache

Auth Service
├── PostgreSQL → auth-postgres
└── Redis DB 2 → cache
```

## Переменные окружения

Перед первым запуском создайте `.env` каждого сервиса:

```bash
cp services/content_service/.env.example \
   services/content_service/.env

cp services/content_etl/.env.example \
   services/content_etl/.env

cp services/auth_service/.env.example \
   services/auth_service/.env

cp services/admin_service/.env.example \
   services/admin_service/.env
```

Файлы `.env` не должны попадать в Git.

## Запуск

Все сервисы:

```bash
docker compose up --build
```

Запуск в фоне:

```bash
docker compose up -d --build
```

Отдельные сервисы из корня репозитория:

```bash
docker compose up --build content-service
docker compose up --build auth-service
docker compose up --build admin-service
docker compose up --build content-etl
```

Compose автоматически запускает зависимости, описанные в `depends_on`.

## Создание администратора

Admin Service не использует отдельную команду `createsuperuser`.

Суперпользователь создаётся в Auth Service:

```bash
docker compose exec auth-service \
  python -m src.commands.create_superuser
```

Данные пользователя задаются в:

```text
services/auth_service/.env
```

После этого пользователь может войти в Django Admin:

```text
http://127.0.0.1:8001/admin/
```

## Просмотр логов

```bash
docker compose logs -f content-service
docker compose logs -f auth-service
docker compose logs -f admin-service
docker compose logs -f content-etl
```

Основные application logs направляются в stdout и stderr контейнеров.