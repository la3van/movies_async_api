# Auth Service

HTTP API для аутентификации, авторизации и управления пользователями онлайн-кинотеатра.

Сервис отвечает за регистрацию и вход пользователей, ротацию refresh-токенов, завершение сессий, управление профилем, ролями и permissions, проверку прав доступа и хранение истории входов. Данные сервиса находятся в отдельной PostgreSQL-базе, а результаты GET-запросов кешируются в Redis.

## Стек

- Python 3.10;
- FastAPI и Uvicorn;
- SQLAlchemy 2.0 Async и asyncpg;
- PostgreSQL 16;
- Alembic;
- Redis 7;
- Pydantic v2;
- PyJWT;
- passlib и bcrypt;
- ORJSONResponse;
- Typer для служебных CLI-команд.

## Архитектура

```text
HTTP endpoint
    ↓
FastAPI dependencies / authentication
    ↓
Service
    ├── Cache interface ───────────────────────── Redis
    └── UnitOfWorkFactory
            ↓
        SQLAlchemyUnitOfWork
            ├── UserRepository
            ├── RoleRepository
            ├── PermissionRepository
            ├── RefreshSessionRepository
            └── LoginHistoryRepository
                    ↓
              одна AsyncSession
                    ↓
                PostgreSQL
```

Endpoints работают с сервисным слоем. Сервисы зависят от интерфейса кеша и фабрики Unit of Work, но не создают SQLAlchemy-сессии и PostgreSQL-репозитории напрямую. `SQLAlchemyUnitOfWork` открывает одну `AsyncSession` на бизнес-операцию и создаёт все нужные репозитории на этой сессии.

FastAPI dependencies собирают сервисы, передавая им `UnitOfWorkFactory` и Redis-кеш. Конкретные PostgreSQL-репозитории создаются только внутри реализации Unit of Work.

## Структура

```text
auth_service/
├── alembic/                  # миграции PostgreSQL
├── src/
│   ├── api/                  # endpoints, dependencies, schemas и handlers
│   ├── cache/                # интерфейс кеша и Redis-реализация
│   ├── commands/             # служебные CLI-команды
│   ├── core/                 # settings, JWT, security и logging
│   ├── db/                   # инициализация PostgreSQL и Redis
│   ├── models/               # SQLAlchemy-модели
│   ├── repositories/
│   │   ├── interfaces/       # контракты репозиториев
│   │   └── postgres/         # реализации для PostgreSQL
│   ├── unit_of_work/         # границы транзакций и SQLAlchemy UoW
│   ├── services/
│   │   ├── cache_keys/       # формирование ключей и шаблонов Redis
│   │   └── ...               # бизнес-логика
│   └── main.py
├── tests/
│   └── functional/           # функциональные HTTP-тесты
├── alembic.ini
├── .coveragerc
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

## Unit of Work и транзакции

`AbstractUnitOfWork` описывает доступные репозитории и операции `commit` / `rollback`. `SQLAlchemyUnitOfWork` является PostgreSQL-реализацией этого контракта.

Типичная операция записи выглядит так:

```python
async with self._uow_factory() as uow:
    user = await uow.users.get_by_id(user_id)
    role = await uow.roles.get_by_id(role_id)

    await uow.users.add_role(user, role)
    await uow.commit()
```

Все репозитории внутри блока используют одну `AsyncSession`, поэтому составная бизнес-операция выполняется в одной транзакции. Успешная запись фиксируется явным `commit()`. Если внутри `async with` возникает исключение, Unit of Work вызывает `rollback()` и в любом случае закрывает сессию.

Для GET-операций используется тот же UoW, но `commit()` не вызывается. Проверка Redis выполняется до открытия UoW, чтобы при cache hit не создавать SQLAlchemy-сессию.

## Основные сущности

| Таблица | Назначение |
| --- | --- |
| `users` | Пользователи и их состояние |
| `roles` | Роли пользователей |
| `permissions` | Права доступа |
| `user_roles` | Связь many-to-many между пользователями и ролями |
| `role_permissions` | Связь many-to-many между ролями и permissions |
| `refresh_sessions` | Refresh-сессии и их состояние |
| `login_history` | История успешных и неуспешных попыток входа |

## Конфигурация

Из каталога `services/auth_service`:

```bash
cp .env.example .env
```

Основные переменные окружения:

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

USER_CACHE_EXPIRE_IN_SECONDS=300
ROLE_CACHE_EXPIRE_IN_SECONDS=300
PERMISSION_CACHE_EXPIRE_IN_SECONDS=300
TOKEN_CLAIMS_CACHE_EXPIRE_IN_SECONDS=300
LOGIN_HISTORY_CACHE_EXPIRE_IN_SECONDS=60

JWT_SECRET_KEY=change_me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

SUPERUSER_LOGIN=admin
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=admin_password
SUPERUSER_FIRST_NAME=Admin
SUPERUSER_LAST_NAME=User
```

В production необходимо заменить `JWT_SECRET_KEY`, пароли БД и данные суперпользователя.

## PostgreSQL и Alembic

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

При обновлении токенов:

1. проверяется refresh-сессия;
2. старая сессия отзывается;
3. создаётся новая refresh-сессия;
4. клиент получает новую пару токенов.

Повторное использование отозванного refresh token запрещено. `logout` отзывает выбранную сессию, а `logout-others` — остальные refresh-сессии текущего пользователя.

## Роли и permissions

- роль может содержать несколько permissions;
- пользователь может иметь несколько ролей;
- permissions пользователя определяются через его роли;
- superuser проходит проверку permissions без явного назначения права;
- роли с `is_default=true` назначаются новым пользователям при регистрации.

Административные операции с ролями, permissions и назначением ролей пользователям доступны только активному superuser.

## Redis-кеширование

Кешируются все GET-endpoints Auth Service:

```text
GET /api/v1/users/me
GET /api/v1/users/me/login-history
GET /api/v1/permissions/
GET /api/v1/permissions/{permission_id}
GET /api/v1/roles/
GET /api/v1/roles/{role_id}
```

Списки permissions, ролей и истории входов кешируются отдельно для каждой комбинации `limit` и `offset`.

Основные зависимости инвалидации:

```text
изменение permission
    → permission item cache
    → permissions list caches
    → role item caches
    → roles list caches
    → user profile caches

изменение или удаление role
    → role item cache
    → roles list caches
    → user profile caches

обновление profile / password / user roles
    → user profile cache

новая попытка login
    → login-history caches пользователя
```

Redis-ключи получают общий префикс из `REDIS_KEY_PREFIX`. В корневом Docker Compose Auth Service использует Redis DB `2`.

## Запуск через Docker Compose

Для доступа с хоста через общую точку входа:

```bash
docker compose up --build nginx
```

Nginx запускает Auth Service и остальные HTTP-сервисы, указанные в его `depends_on`.

Запуск только Auth Service для внутренних проверок:

```bash
docker compose up --build auth-service
```

В этом режиме сервис доступен контейнерам по адресу `auth-service:8000`, но его порт не опубликован на хост.

Запуск всего окружения:

```bash
docker compose up --build
```

Логи сервиса и reverse proxy:

```bash
docker compose logs -f auth-service nginx
```

Перед запуском приложения контейнер применяет Alembic-миграции.

## Локальный запуск

Из каталога `services/auth_service`:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Укажите в `.env` адреса PostgreSQL и Redis, доступные с хоста, затем выполните:

```bash
alembic upgrade head
PYTHONPATH=src uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload
```

## Создание superuser

Команда использует переменные `SUPERUSER_*` из окружения:

```bash
PYTHONPATH=src python -m src.commands.create_superuser
```

Если пользователь с таким логином уже существует, команда активирует его и выдаёт права superuser. Конфликт существующего email с другим логином завершает команду с ошибкой.

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

В корневом Compose Auth Service не публикует собственный порт. Внешние запросы маршрутизирует Nginx на `127.0.0.1:8000`:

- Swagger UI: `http://127.0.0.1:8000/docs`;
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`;
- healthcheck: `http://127.0.0.1:8000/health`;
- базовый API-префикс: `/api/v1`.

Внутри Docker-сети Admin Service и другие контейнеры обращаются к Auth Service напрямую по адресу `http://auth-service:8000`.

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
GET    /api/v1/users/me
PATCH  /api/v1/users/me
PATCH  /api/v1/users/me/password
GET    /api/v1/users/me/login-history
POST   /api/v1/users/{user_id}/roles/{role_id}
DELETE /api/v1/users/{user_id}/roles/{role_id}
```

### Permissions

```text
POST  /api/v1/permissions/
GET   /api/v1/permissions/
GET   /api/v1/permissions/{permission_id}
PATCH /api/v1/permissions/{permission_id}
POST  /api/v1/permissions/check
```

### Roles

```text
POST   /api/v1/roles/
GET    /api/v1/roles/
GET    /api/v1/roles/{role_id}
PATCH  /api/v1/roles/{role_id}
DELETE /api/v1/roles/{role_id}
```

## Авторизация запросов

Для защищённых endpoints используется Bearer access token:

```http
Authorization: Bearer <access_token>
```

Access token должен быть валидным, неистёкшим и принадлежать активному пользователю. Refresh token нельзя использовать вместо access token.

## Функциональные тесты

Тесты находятся в [`tests/functional`](tests/functional) и выполняют реальные HTTP-запросы к Auth Service с отдельными PostgreSQL и Redis. Через публичный API проверяется вся цепочка `endpoint → service → Unit of Work → repositories → PostgreSQL`, а также Redis-кеширование и инвалидация.

В исходном коде находится `137` тестовых функций. За счёт параметризации они разворачиваются в `246` сценариев.

Последний зафиксированный результат:

```text
246 passed
1344 statements
174 missed
148 branches
9 partial branches
81% total coverage
```

Подробная инструкция: [`tests/README.md`](tests/README.md).

## Проверка типов

Из каталога `services/auth_service`:

```bash
mypy src
```