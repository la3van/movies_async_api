# Auth Service

HTTP API для аутентификации, авторизации и управления пользователями онлайн-кинотеатра.

Сервис отвечает за регистрацию, вход, refresh-token rotation, logout, профили пользователей, роли, permissions и проверку прав. Данные хранятся в отдельной PostgreSQL-базе, а read-запросы кешируются в Redis.

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
- passlib и bcrypt;
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

## Структура

```text
auth_service/
├── alembic/                  # миграции PostgreSQL
├── src/
│   ├── api/                  # endpoints, роутеры и API-схемы
│   ├── cache/                # кеш и Redis-реализация
│   ├── commands/             # служебные команды
│   ├── core/                 # settings, JWT, security и logging
│   ├── db/                   # PostgreSQL и Redis clients
│   ├── models/               # SQLAlchemy-модели
│   ├── repositories/
│   │   ├── interfaces/       # контракты репозиториев
│   │   └── postgres/         # реализации PostgreSQL
│   ├── services/             # бизнес-логика
│   └── main.py
├── tests/
├── alembic.ini
├── .coveragerc
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

## Основные сущности

| Таблица | Назначение |
| --- | --- |
| `users` | Пользователи |
| `roles` | Роли |
| `permissions` | Разрешения |
| `user_roles` | Связь пользователей и ролей |
| `role_permissions` | Связь ролей и permissions |
| `refresh_sessions` | Refresh-token сессии |
| `login_history` | История успешных и неуспешных входов |

## Конфигурация

Из каталога `services/auth_service`:

```bash
cp .env.example .env
```

Основные настройки:

```env
PROJECT_NAME=auth-service
DEBUG=true

AUTH_SERVICE_HOST=0.0.0.0
AUTH_SERVICE_PORT=8000

POSTGRES_HOST=auth-postgres
POSTGRES_PORT=5432
POSTGRES_DB=auth
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=auth_password
POSTGRES_CONNECT_TIMEOUT=5
POSTGRES_STATEMENT_TIMEOUT_MS=30000

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=2
REDIS_KEY_PREFIX=auth
REDIS_SOCKET_CONNECT_TIMEOUT=5
REDIS_SOCKET_TIMEOUT=5
REDIS_MAX_RETRIES=2
REDIS_RETRY_BACKOFF_BASE=0.1
REDIS_RETRY_BACKOFF_CAP=1.0

JWT_SECRET_KEY=change_me_to_strong_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

SUPERUSER_LOGIN=admin
SUPERUSER_PASSWORD=admin
SUPERUSER_FIRST_NAME=Admin
SUPERUSER_LAST_NAME=User
```

Для production необходимо заменить `JWT_SECRET_KEY`, пароли БД и данные superuser.

## PostgreSQL и Alembic

Auth Service использует отдельную PostgreSQL-базу.

Применить миграции:

```bash
alembic upgrade head
```

Создать миграцию после изменения моделей:

```bash
alembic revision --autogenerate -m "migration message"
```

Проверить текущую ревизию:

```bash
alembic current
```

## JWT и refresh-token rotation

| Токен | Назначение |
| --- | --- |
| `access_token` | Короткоживущий JWT для защищённых запросов |
| `refresh_token` | Opaque token для обновления пары токенов |

Refresh token не хранится в открытом виде. В `refresh_sessions` сохраняется его SHA-256 hash.

При refresh:

1. старая refresh-сессия отзывается;
2. создаётся новая сессия;
3. клиент получает новую пару токенов.

Logout отзывает текущую сессию, а logout others — остальные refresh-сессии пользователя.

## Redis

Redis кеширует read endpoints, включая:

```text
GET /api/v1/users/me
GET /api/v1/users/me/login-history
GET /api/v1/permissions/{permission_id}
GET /api/v1/roles/{role_id}
```

После изменения пользователей, ролей и permissions соответствующие записи кеша обновляются или удаляются.

В корневом Docker Compose Auth Service использует Redis DB `2`.

## Запуск через Docker Compose

Из корня репозитория:

```bash
docker compose up --build auth-service
```

Полное окружение:

```bash
docker compose up --build
```

Логи:

```bash
docker compose logs -f auth-service
```

Контейнер применяет Alembic-миграции перед запуском приложения.

## Локальный запуск

Из каталога `services/auth_service`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Укажите в `.env` адреса PostgreSQL и Redis, доступные с хоста.

```bash
alembic upgrade head
PYTHONPATH=src uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

## Healthcheck

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

В корневом Compose сервис опубликован на порту `8008`:

- Swagger UI: `http://localhost:8008/docs`
- OpenAPI JSON: `http://localhost:8008/openapi.json`
- базовый API-префикс: `/api/v1`

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

Операции управления ролями и permissions доступны superuser.

## Функциональные тесты

Тесты находятся в [`tests/functional`](tests/functional) и используют отдельные PostgreSQL и Redis.

Инструкции: [tests/README.md](tests/README.md).

На момент текущего рефакторинга зафиксировано `76%` покрытия кода. Дальнейшая работа по расширению тестов описана в TODO тестового README.

## Проверка типов

Из каталога `services/auth_service`:

```bash
mypy src
```
