# Auth Service functional tests

Функциональные тесты проверяют Auth Service через реальные HTTP-запросы в изолированном Docker Compose окружении.

## Что запускается

`functional/docker-compose.yml` поднимает:

| Сервис | Назначение |
| --- | --- |
| `auth-service` | Тестируемое FastAPI-приложение под coverage.py |
| `auth-postgres` | Изолированная PostgreSQL-база |
| `redis` | Изолированный Redis для кеша |
| `tests` | Контейнер с pytest |

Перед запуском приложения контейнер `auth-service` применяет Alembic-миграции.

## Структура

```text
tests/
├── functional/
│   ├── coverage/
│   ├── fixtures/
│   │   ├── auth.py
│   │   ├── common.py
│   │   ├── http.py
│   │   ├── postgres.py
│   │   └── redis.py
│   ├── src/
│   │   ├── auth/
│   │   │   └── test_auth.py
│   │   ├── permissions/
│   │   │   └── test_permissions.py
│   │   ├── roles/
│   │   │   └── test_roles_permissions.py
│   │   └── users/
│   │       └── test_users.py
│   ├── test_data/
│   │   ├── auth.py
│   │   ├── permissions.py
│   │   ├── responses.py
│   │   ├── roles.py
│   │   └── users.py
│   ├── utils/
│   │   └── helpers.py
│   ├── conftest.py
│   ├── settings.py
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env
│   └── .env.example
└── README.md
```

## Организация фикстур

`conftest.py` регистрирует fixture-модули через `pytest_plugins`.

Фикстуры разделены на:

- инфраструктурные: HTTP, PostgreSQL, Redis и event loop;
- auth-фикстуры: пользователь, login, access headers и superuser;
- предметные: role, permission и user with role;
- helper-фикстуры: SQL-проверки side effects и cache-сценариев.

PostgreSQL и Redis очищаются до и после каждого теста.

## Подготовка окружения

Из корня репозитория:

```bash
cd services/auth_service/tests/functional
cp .env.example .env
```

Тестовый Redis-клиент должен использовать ту же Redis DB, что и Auth Service в тестовом Compose.

## Запуск всех тестов

```bash
docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```

Порядок запуска:

```text
auth-postgres healthy
redis healthy
alembic upgrade head
auth-service healthy
tests start
```

Отдельные `wait_for_postgres.py`, `wait_for_redis.py` и `wait_for_service.py` не нужны: готовность контролируют Docker healthchecks.

## Прогресс тестов

```bash
pytest -vv -s -ra \
  --tb=short \
  --color=yes \
  -o console_output_style=progress-even-when-capture-no \
  tests/functional/src
```

Опция `progress-even-when-capture-no` сохраняет проценты выполнения при использовании `-s`.

## Покрываемые сценарии

### Auth

- регистрация пользователя;
- duplicate login и email;
- валидация email и password;
- login и неверные credentials;
- refresh-token rotation;
- запрет повторного использования revoked token;
- logout и logout others;
- запись успешных и неуспешных входов.

### Users

- получение и обновление профиля;
- кеширование профиля;
- смена пароля;
- отзыв refresh-сессий после смены пароля;
- история входов;
- назначение и удаление роли;
- очистка кеша пользователя.

### Permissions

- создание, список и получение по UUID;
- валидация и duplicate code;
- кеширование и обновление кеша;
- проверка permission через роль;
- superuser-доступ;
- запрет административных операций обычному пользователю.

### Roles

- создание, список, получение и обновление;
- duplicate name;
- привязка permissions;
- кеширование и invalidation;
- удаление роли;
- `404` и ошибки UUID.

## Проверка Redis-кеша

Типичный cache-тест:

1. выполнить HTTP-запрос;
2. убедиться, что ответ сохранён в Redis;
3. изменить или удалить запись напрямую в PostgreSQL;
4. повторить запрос;
5. проверить, что сервис вернул кешированный ответ.

Cache invalidation проверяется после изменения пользователя, роли и permission.

## Изоляция данных

Перед каждым тестом очищаются:

```text
user_roles
role_permissions
login_history
refresh_sessions
users
roles
permissions
```

`alembic_version` сохраняется. Redis очищается через `flushdb()`.

## Запуск отдельной группы или теста

Все auth-тесты:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/auth
```

Один файл:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/users/test_users.py
```

Один тест:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/auth/test_auth.py::test_register_user
```

## Coverage

Текстовый отчёт:

```bash
docker compose run --rm --no-deps auth-service coverage report -m
```

HTML-отчёт:

```bash
docker compose run --rm --no-deps auth-service coverage html
```

Открыть на macOS:

```bash
open coverage/htmlcov/index.html
```

На момент текущего рефакторинга:

```text
TOTAL: 1315 statements, 251 missed, 76% coverage
```

Слабее всего покрыты отдельные ветви и сценарии в:

- `src/commands/create_superuser.py`;
- `src/services/auth.py`;
- `src/services/permission.py`;
- `src/services/role.py`;
- `src/services/user.py`;
- `src/repositories/postgres/user.py`;
- части PostgreSQL-репозиториев и cache error paths.

## TODO

- [ ] Дописать тесты Auth Service до почти полного покрытия кода — ориентир `95%+`.
- [ ] Покрыть команду создания superuser.
- [ ] Добавить сценарии для непокрытых ветвей auth-, user-, role- и permission-сервисов.
- [ ] Добавить негативные сценарии ошибок PostgreSQL и Redis, где это оправдано и не требует хрупких моков.
- [ ] Покрыть оставшиеся ветви token rotation, revoke и cache invalidation.

## Остановка и очистка

```bash
docker compose down -v --remove-orphans
```

`-v` полностью пересоздаёт тестовую PostgreSQL-базу и Redis при следующем запуске.

## Полезные команды

Логи Auth Service:

```bash
docker compose logs auth-service
```

Подключиться к тестовой базе:

```bash
docker compose exec auth-postgres \
  psql -U auth_user -d auth_test
```

Показать таблицы:

```bash
docker compose exec auth-postgres \
  psql -U auth_user -d auth_test -c "\\dt"
```

Проверить Compose-конфигурацию:

```bash
docker compose config
```
