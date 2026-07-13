# Auth Service functional tests

Функциональные тесты проверяют Auth Service через реальные HTTP-запросы в изолированном Docker Compose окружении.

Тесты проходят всю рабочую цепочку:

```text
HTTP request
    → FastAPI routing и validation
    → authentication / dependencies
    → service layer
    → PostgreSQL и Redis
    → HTTP response
```

Моки сервисов и репозиториев не используются. Ошибочные payload, path/query-параметры, права доступа, кеширование и побочные эффекты проверяются на реальной тестовой инфраструктуре.

## Что запускается

`docker-compose.yml` поднимает:

| Сервис | Назначение |
| --- | --- |
| `auth-service` | Тестируемое FastAPI-приложение, запущенное под coverage.py |
| `auth-postgres` | Изолированная PostgreSQL-база |
| `redis` | Изолированный Redis для кеша |
| `tests` | Контейнер с pytest |

Перед запуском приложения контейнер `auth-service` применяет Alembic-миграции.

## Структура

```text
tests/functional/
├── coverage/                  # .coverage и HTML-отчёт
├── fixtures/
│   ├── auth.py                # пользователи, токены и auth headers
│   ├── common.py              # общие предметные фикстуры
│   ├── http.py                # HTTP request helpers
│   ├── postgres.py            # PostgreSQL cleanup и SQL helpers
│   └── redis.py               # Redis client и cleanup
├── src/
│   ├── auth/
│   │   ├── test_register.py
│   │   ├── test_login.py
│   │   ├── test_refresh.py
│   │   └── test_logout.py
│   ├── permissions/
│   │   ├── test_create_permission.py
│   │   ├── test_get_permissions.py
│   │   ├── test_update_permission.py
│   │   └── test_check_permission.py
│   ├── roles/
│   │   ├── test_create_role.py
│   │   ├── test_get_roles.py
│   │   ├── test_update_role.py
│   │   └── test_delete_role.py
│   └── users/
│       ├── test_get_user.py
│       ├── test_update_user.py
│       ├── test_password.py
│       ├── test_login_history.py
│       └── test_user_roles.py
├── test_data/
│   ├── auth.py
│   ├── common.py              # UNSET sentinel для PATCH payload
│   ├── permissions.py
│   ├── responses.py
│   ├── roles.py
│   └── users.py
├── utils/
│   └── helpers.py
├── conftest.py
├── settings.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

В наборе находятся `137` тестовых функций. За счёт `pytest.mark.parametrize` они разворачиваются в `246` отдельных тестовых сценариев.

## Организация тестовых данных

`test_data` содержит константы и функции создания request payload. Для PATCH-запросов используется sentinel `UNSET`, который позволяет различать:

```python
get_update_data()
# поле отсутствует в JSON

get_update_data(description=None)
# поле явно передано как null

get_update_data(description='new value')
# передано новое значение
```

Это важно, поскольку «не изменять поле» и «очистить поле» являются разными API-сценариями.

## Организация фикстур

`conftest.py` регистрирует fixture-модули через `pytest_plugins`.

Фикстуры разделены на:

- HTTP-клиент и request helpers;
- очистку и прямые проверки PostgreSQL;
- очистку и прямые проверки Redis;
- регистрацию, login, access headers и superuser;
- создание пользователей, ролей и permissions;
- вспомогательные сценарии назначения ролей и проверки side effects.

PostgreSQL и Redis очищаются до и после каждого теста. `alembic_version` при очистке PostgreSQL сохраняется.

## Подготовка окружения

Из корня репозитория:

```bash
cd services/auth_service/tests/functional
cp .env.example .env
```

Тестовый Redis-клиент должен использовать ту же Redis DB, что и Auth Service в тестовом Compose.

## Полный запуск

```bash
docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests
```

Порядок запуска:

```text
auth-postgres healthy
redis healthy
alembic upgrade head
auth-service healthy
tests start
```

Готовность компонентов контролируется Docker healthchecks.

После завершения:

```bash
docker compose down -v --remove-orphans
```

`-v` удаляет тестовые volumes, поэтому PostgreSQL и Redis будут полностью пересозданы при следующем запуске.

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
  tests/functional/src/users/test_get_user.py
```

Один тест:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/auth/test_register.py::test_register_user
```

## Покрываемые категории сценариев

Для публичных endpoints проверяются:

- положительные сценарии;
- бизнес-ошибки: duplicate, not found, invalid credentials и revoked session;
- отсутствие access token;
- недостаточные права;
- неактивный пользователь;
- невалидные UUID;
- неправильные query-параметры и границы пагинации;
- отсутствующие обязательные поля;
- `null`, неверные типы, пустые строки и ограничения длины;
- частичные PATCH-запросы;
- явная очистка nullable-полей;
- пустые PATCH payload;
- PostgreSQL side effects;
- Redis cache hit и cache invalidation.

## Auth

Проверяются:

- регистрация пользователя;
- назначение default-role при регистрации;
- duplicate login и email;
- валидация регистрационных данных;
- успешный login;
- неверные credentials;
- login неактивного пользователя;
- запись успешных и неуспешных попыток входа;
- refresh-token rotation;
- запрет повторного использования revoked token;
- истёкшая, несуществующая и отозванная refresh-сессия;
- `logout` и `logout-others`;
- невалидные request payload.

## Users

Проверяются:

- получение профиля;
- cache hit профиля;
- частичное обновление профиля;
- очистка nullable-полей через `null`;
- инвалидация profile cache;
- смена пароля;
- неправильный старый пароль;
- отзыв refresh-сессий после смены пароля;
- получение истории входов;
- cache hit истории входов;
- инвалидация истории после новой попытки login;
- пагинация и невалидные query-параметры;
- назначение и удаление роли;
- отсутствующий пользователь или роль;
- невалидные UUID;
- инвалидация profile cache после изменения ролей.

## Permissions

Проверяются:

- создание permission;
- duplicate code;
- создание без необязательного description;
- валидация request payload;
- получение списка и пагинация;
- получение permission по UUID;
- `404` для отсутствующей permission;
- cache hit списка;
- cache hit отдельной permission;
- инвалидация list cache после создания;
- полное и частичное обновление;
- очистка description через `null`;
- пустой PATCH;
- duplicate code при обновлении;
- каскадная инвалидация permission, role и user caches;
- проверка permission через роль;
- отсутствие permission;
- автоматический доступ superuser;
- запрет административных операций обычному пользователю.

## Roles

Проверяются:

- создание роли;
- создание роли с permissions;
- duplicate name;
- отсутствующая permission при создании или обновлении;
- валидация request payload;
- получение списка и пагинация;
- получение роли по UUID;
- `404` и ошибки UUID;
- cache hit списка;
- cache hit отдельной роли;
- инвалидация list cache после создания;
- полное и частичное обновление;
- изменение `is_default`;
- очистка description и списка permissions;
- пустой PATCH;
- каскадная инвалидация role и user caches;
- удаление роли;
- удаление отсутствующей роли;
- запрет административных операций обычному пользователю.

## Проверка Redis-кеша

Каждый кешируемый GET имеет отдельный cache-hit сценарий:

```text
GET /api/v1/users/me
GET /api/v1/users/me/login-history
GET /api/v1/permissions/
GET /api/v1/permissions/{permission_id}
GET /api/v1/roles/
GET /api/v1/roles/{role_id}
```

Типичный cache-hit тест:

1. выполнить GET и заполнить Redis;
2. изменить или удалить исходные данные напрямую в PostgreSQL;
3. повторить тот же GET;
4. убедиться, что сервис вернул ранее закешированный результат.

Два одинаковых GET подряд сами по себе не доказывают чтение из Redis, поэтому тесты намеренно изменяют состояние PostgreSQL между запросами.

Cache invalidation проверяется после:

- создания и обновления permissions;
- создания, обновления и удаления ролей;
- изменения профиля и пароля;
- назначения и удаления пользовательской роли;
- успешных и неуспешных попыток login.

## Валидационные тесты и параметризация

Похожие некорректные входные данные объединены через `pytest.mark.parametrize`. Один тестовый метод может проверять несколько вариантов:

```text
missing field
null
wrong type
too short
too long
invalid UUID
invalid pagination
```

Поэтому число `246 passed` означает количество развёрнутых сценариев, а не количество отдельных функций в исходном коде.

При проверке `422` предпочтительно проверять поле из `detail[*].loc` и тип ошибки, а не полный текст сообщения Pydantic.

## Coverage

Coverage запускается внутри контейнера `auth-service` вместе с Uvicorn:

```text
coverage run --rcfile=.coveragerc -m uvicorn ...
```

Включено branch coverage:

```ini
[run]
source = src
branch = True
sigterm = True
```

Последний зафиксированный результат:

```text
246 passed
1373 statements
236 missed
150 branches
10 partial branches
78% total coverage
```

`skip_empty = True` исключает из отчёта пустые Python-файлы, например пустые `__init__.py`. Сообщение `13 empty files skipped` не относится к Markdown, JSON или другим непитоновским файлам.

Слабее всего функциональными тестами покрываются внутренние аварийные ветви:

- ошибки `commit`, `flush` и `rollback`;
- недоступность PostgreSQL или Redis во время конкретной операции;
- отдельные внутренние ветви сервисов и репозиториев;
- CLI-команда `create_superuser`.

Это ожидаемо для набора, ограниченного функциональными HTTP-тестами. Цель тестов — покрыть пользовательские и API-сценарии, а не искусственно вызывать каждую внутреннюю ошибку ради процента.

### Получить текстовый отчёт

После полного прогона и остановки `auth-service`:

```bash
docker compose run --rm --no-deps \
  auth-service coverage report -m
```

### Создать HTML-отчёт

```bash
docker compose run --rm --no-deps \
  auth-service coverage html
```

Открыть на macOS:

```bash
open coverage/htmlcov/index.html
```

### Полностью пересоздать coverage

```bash
docker compose down -v --remove-orphans
rm -f coverage/.coverage

docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests

docker compose run --rm --no-deps \
  auth-service coverage report -m
```

`auth-service` должен корректно завершиться, чтобы coverage.py сохранил данные процесса Uvicorn.

## Полезные команды

Логи Auth Service:

```bash
docker compose logs --tail=200 auth-service
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