# Auth Service

HTTP API для аутентификации, авторизации и управления пользователями онлайн-кинотеатра.

Сервис отвечает за регистрацию, вход, refresh-token rotation, logout, роли, permissions и проверку прав пользователя. Данные хранятся в PostgreSQL, а часто запрашиваемые ответы кешируются в Redis.

## Стек

- Python 3.10;
- FastAPI;
- Uvicorn;
- SQLAlchemy 2.0 async;
- asyncpg;
- Alembic;
- PostgreSQL;
- Redis;
- Pydantic v2;
- PyJWT;
- passlib + bcrypt;
- ORJSONResponse.

## Архитектура

```text
HTTP endpoint
    ↓
Service
    ├── Cache
    │      ↑
    │   Redis
    └── Repository interface
           ↑
      PostgreSQL repository
```

Сервис организован по слоям:

| Каталог | Назначение |
| --- | --- |
| `src/api/` | FastAPI endpoints, API schemas и роутеры |
| `src/services/` | Бизнес-логика auth-сервиса |
| `src/repositories/interfaces/` | Контракты репозиториев |
| `src/repositories/postgres/` | PostgreSQL-реализации репозиториев |
| `src/models/` | SQLAlchemy-модели |
| `src/db/` | Инициализация PostgreSQL и Redis |
| `src/core/` | Настройки, JWT, security-утилиты и логирование |
| `src/main.py` | Создание FastAPI-приложения |
| `alembic/` | Миграции БД |

## Основные сущности

| Сущность | Назначение |
| --- | --- |
| `users` | Пользователи сервиса |
| `roles` | Роли пользователей |
| `permissions` | Разрешения для проверки доступа |
| `user_roles` | Связь пользователей и ролей |
| `role_permissions` | Связь ролей и permissions |
| `refresh_sessions` | Refresh-token сессии |
| `login_history` | История успешных и неуспешных входов |

## Конфигурация

Создайте файл окружения:

```bash
cp .env.example .env
```

Основные переменные:

```env
PROJECT_NAME=auth-service
DEBUG=true

# Auth API
AUTH_SERVICE_HOST=0.0.0.0
AUTH_SERVICE_PORT=8000

# PostgreSQL
POSTGRES_HOST=auth-postgres
POSTGRES_PORT=5432
POSTGRES_DB=auth
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=auth_password
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_STATEMENT_TIMEOUT_MS=30000

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=2
REDIS_KEY_PREFIX=auth
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_MAX_RETRIES=2
REDIS_RETRY_BACKOFF_BASE=0.1
REDIS_RETRY_BACKOFF_CAP=1.0

# JWT
JWT_SECRET_KEY=change_me_to_strong_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Superuser
SUPERUSER_LOGIN=admin
SUPERUSER_PASSWORD=admin
SUPERUSER_FIRST_NAME=Admin
SUPERUSER_LAST_NAME=User
```

`JWT_SECRET_KEY` в реальном окружении должен быть заменён на сильный случайный секрет.

## PostgreSQL

Auth Service использует отдельную PostgreSQL базу. Таблицы создаются через Alembic-миграции.

Применить миграции:

```bash
alembic upgrade head
```

Создать новую миграцию после изменения моделей:

```bash
alembic revision --autogenerate -m "migration message"
```

## Redis

Redis используется для кеширования read-запросов и ускорения повторных обращений.

Кешируются отдельные read endpoints, например:

```text
GET /api/v1/users/me
GET /api/v1/users/me/login-history
GET /api/v1/permissions/{permission_id}
GET /api/v1/roles/{role_id}
```

После изменения пользователя, роли или permission сервис очищает или обновляет соответствующий кеш.

## JWT и refresh-token rotation

Auth Service использует два типа токенов:

| Токен | Назначение |
| --- | --- |
| `access_token` | Короткоживущий JWT для авторизации запросов |
| `refresh_token` | Opaque token для обновления пары токенов |

Refresh token не хранится в БД в открытом виде. В `refresh_sessions` сохраняется только SHA-256 hash токена.

При refresh выполняется rotation:

1. старый refresh token отзывается;
2. создаётся новая refresh-сессия;
3. клиент получает новую пару `access_token` + `refresh_token`.

Logout отзывает текущую refresh-сессию. Logout others отзывает все refresh-сессии пользователя, кроме текущей.

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up --build auth-service
```

Обычно сервис запускается вместе с PostgreSQL и Redis:

```bash
docker compose up --build
```

После изменения миграций или структуры БД можно выполнить чистый запуск:

```bash
docker compose down -v
docker compose up --build
```

`down -v` удаляет volumes текущего Compose-проекта, включая PostgreSQL и Redis.

## Локальный запуск

Из каталога `auth_service`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Для локального запуска в `.env` укажите доступные с хоста адреса PostgreSQL и Redis, например `localhost`.

Примените миграции:

```bash
alembic upgrade head
```

Запустите приложение:

```bash
PYTHONPATH=src uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

Docker-образ использует тот же entry point без `--reload`.

## Healthcheck

Проверка доступности сервиса:

```text
GET /health
```

Успешный ответ:

```json
{
  "status": "ok"
}
```

## Документация API

- Swagger UI: `http://localhost:8008/docs`
- OpenAPI JSON: `http://localhost:8008/openapi.json`

Базовый API-префикс:

```text
/api/v1
```

## Endpoints

### Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
POST /api/v1/auth/logout-others
```

### Users

```text
GET /api/v1/users/me
PATCH /api/v1/users/me
PATCH /api/v1/users/me/password
GET /api/v1/users/me/login-history
POST /api/v1/users/{user_id}/roles/{role_id}
DELETE /api/v1/users/{user_id}/roles/{role_id}
```

### Permissions

```text
POST /api/v1/permissions/
GET /api/v1/permissions/
GET /api/v1/permissions/{permission_id}
PATCH /api/v1/permissions/{permission_id}
POST /api/v1/permissions/check
```

### Roles

```text
POST /api/v1/roles/
GET /api/v1/roles/
GET /api/v1/roles/{role_id}
PATCH /api/v1/roles/{role_id}
DELETE /api/v1/roles/{role_id}
```

## Авторизация

Для защищённых endpoints используется Bearer access token:

```http
Authorization: Bearer <access_token>
```

Обычные пользователи могут работать со своим профилем и проверять permissions.

Операции управления ролями и permissions доступны только superuser.

## Проверка типов

Из каталога `auth_service`:

```bash
mypy src
```

## Функциональные тесты

Функциональные тесты находятся в:

```text
tests/functional
```

Они запускаются в отдельном Docker Compose окружении и проверяют сервис через реальные HTTP-запросы.

Инструкции: [tests/README.md](tests/README.md).
