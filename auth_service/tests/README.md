# Functional tests

Функциональные тесты проверяют Auth Service через реальные HTTP-запросы в изолированном Docker Compose окружении.

## Что запускается

`tests/functional/docker-compose.yml` поднимает:

| Сервис | Назначение |
| --- | --- |
| `auth-service` | Тестируемое FastAPI-приложение |
| `auth-postgres` | Изолированная PostgreSQL база для auth-сервиса |
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

Тестовые файлы организованы по endpoint-группам. Подготовка данных вынесена в fixtures: тесты получают готового пользователя, superuser, role или permission через аргументы pytest.

## Организация фикстур

Корневой `conftest.py` регистрирует fixture-модули через `pytest_plugins`.

Фикстуры разделены на:

- инфраструктурные: HTTP, PostgreSQL, Redis и event loop;
- auth-фикстуры: регистрация пользователя, логин, superuser, headers;
- предметные: созданные role, permission, user with role;
- helper-фикстуры: SQL-запросы для проверки side effects и cache-сценариев.

PostgreSQL и Redis очищаются до и после каждого теста.

## Подготовка окружения

Команды выполняются из каталога:

```bash
cd auth_service/tests/functional
```

Создайте локальный `.env`:

```bash
cp .env.example .env
```

Тестовый Redis-клиент должен использовать ту же Redis DB, что и Auth Service в тестовом Compose, чтобы autouse-фикстура действительно очищала кеш приложения.

## Запуск всех тестов

Из каталога `auth_service/tests/functional`:

```bash
docker compose up --build \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```

Команда:

1. собирает образы;
2. поднимает PostgreSQL и Redis;
3. ждёт их `healthcheck`;
4. запускает `auth-service`;
5. применяет Alembic-миграции;
6. ждёт `/health`;
7. запускает pytest;
8. завершает Compose с exit-code контейнера `tests`.

Не прерывайте остановку Compose повторным `Ctrl+C`: coverage сохраняет данные при корректном завершении API-контейнера.

## Остановка и очистка

Остановить контейнеры:

```bash
docker compose down
```

Остановить контейнеры и удалить тестовые volume:

```bash
docker compose down -v
```

`down -v` полезен, если нужно полностью пересоздать тестовую PostgreSQL базу.

## Логи и прогресс тестов

Тесты запускаются с подробным выводом:

```bash
pytest -vv -s -ra --tb=short --color=yes tests/functional/src
```

Пример вывода:

```text
tests/functional/src/auth/test_auth.py::test_register_user PASSED [  1%]
tests/functional/src/roles/test_roles_permissions.py::test_get_role_from_redis PASSED [ 60%]
tests/functional/src/users/test_users.py::test_remove_role_clears_user_redis_cache PASSED [100%]
```

Флаги:

- `-vv` — подробный вывод каждого теста;
- `-s` — не скрывать stdout/stderr;
- `-ra` — summary по skipped/failed/xfailed;
- `--tb=short` — короткий traceback;
- `--color=yes` — цветной вывод.

## Healthcheck-и

В тестовом окружении готовность сервисов проверяется через Docker Compose healthcheck.

Порядок запуска:

```text
auth-postgres healthy
redis healthy
auth-service healthy
tests start
```

Поэтому отдельные `wait_for_postgres.py`, `wait_for_redis.py` и `wait_for_service.py` не нужны.

## Покрываемые сценарии

### Auth

- регистрация пользователя;
- запрет регистрации с duplicate login;
- запрет регистрации с duplicate email;
- валидация email;
- валидация короткого password;
- login;
- login с неверным password;
- login несуществующего пользователя;
- refresh-token rotation;
- запрет повторного использования revoked refresh-token;
- refresh с invalid token;
- logout;
- logout с invalid token;
- logout others;
- запись успешных и неуспешных попыток входа в `login_history`.

### Users

- получение текущего пользователя;
- получение текущего пользователя из Redis;
- запрет получения профиля без access-token;
- запрет получения профиля с invalid access-token;
- обновление профиля;
- обновление кеша после изменения профиля;
- смена пароля;
- отзыв refresh-сессий после смены пароля;
- ошибка смены пароля с неверным старым паролем;
- получение login history;
- получение login history из Redis;
- валидация query-параметров login history;
- назначение роли пользователю;
- запрет назначения роли обычным пользователем;
- ошибка назначения несуществующей роли;
- удаление роли у пользователя;
- очистка Redis-кеша пользователя после назначения и удаления роли.

### Permissions

- создание permission;
- запрет создания permission обычным пользователем;
- ошибка создания duplicate permission;
- получение списка permissions;
- валидация query-параметров списка permissions;
- получение permission по UUID;
- получение permission из Redis;
- `404` для отсутствующего permission;
- `422` для некорректного UUID;
- обновление permission;
- обновление Redis-кеша после изменения permission;
- ошибка обновления permission на duplicate code;
- проверка отсутствующего permission у обычного пользователя;
- проверка permission через роль пользователя;
- проверка любого permission у superuser;
- запрет проверки permission без access-token.

### Roles

- создание роли;
- запрет создания роли обычным пользователем;
- ошибка создания duplicate role;
- ошибка создания роли с несуществующим permission;
- получение списка ролей;
- валидация query-параметров списка ролей;
- получение роли по UUID;
- получение роли из Redis;
- `404` для отсутствующей роли;
- `422` для некорректного UUID;
- обновление роли;
- обновление Redis-кеша после изменения роли;
- ошибка обновления роли на duplicate name;
- удаление роли;
- очистка Redis-кеша после удаления роли;
- ошибка удаления несуществующей роли.

## Проверка Redis-кеша

Тесты кеша работают по схеме:

1. первый запрос получает объект из PostgreSQL;
2. сервис сохраняет ответ в Redis;
3. тест напрямую удаляет объект из PostgreSQL;
4. повторный запрос должен вернуть прежний результат из Redis.

Такие проверки есть для:

```text
GET /api/v1/users/me
GET /api/v1/users/me/login-history
GET /api/v1/permissions/{permission_id}
GET /api/v1/roles/{role_id}
```

Также проверяется cache invalidation после:

```text
PATCH /api/v1/users/me
POST /api/v1/users/{user_id}/roles/{role_id}
DELETE /api/v1/users/{user_id}/roles/{role_id}
PATCH /api/v1/permissions/{permission_id}
PATCH /api/v1/roles/{role_id}
DELETE /api/v1/roles/{role_id}
```

## Изоляция данных

Перед каждым тестом очищаются таблицы auth-сервиса:

```text
user_roles
role_permissions
login_history
refresh_sessions
users
roles
permissions
```

Таблица `alembic_version` не очищается, потому что она нужна Alembic для понимания применённых миграций.

Redis очищается через `flushdb()` до и после каждого теста.

## Запуск отдельной группы, файла или теста

Запуск всех auth-тестов:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes tests/functional/src/auth
```

Запуск одного endpoint-файла:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes tests/functional/src/users/test_users.py
```

Запуск одного теста:

```bash
docker compose run --rm tests \
  pytest -vv -s -ra --tb=short --color=yes \
  tests/functional/src/auth/test_auth.py::test_register_user
```

После изменения кода Auth Service пересоберите образ:

```bash
docker compose up --build --force-recreate \
  --abort-on-container-exit \
  --exit-code-from tests \
  tests
```

## Coverage

Coverage собирается для кода Auth Service из `auth_service/src`.

Ожидаемый файл покрытия:

```text
tests/functional/coverage/.coverage
```

Текстовый отчёт:

```bash
docker compose run --rm --no-deps auth-service \
  coverage report --rcfile=.coveragerc -m
```

HTML-отчёт:

```bash
docker compose run --rm --no-deps auth-service \
  coverage html --rcfile=.coveragerc
```

Открыть на macOS:

```bash
open coverage/htmlcov/index.html
```

Если coverage пишет:

```text
No data to report.
```

значит файл `.coverage` не был создан или команда `coverage report` смотрит не туда.

## Полезные команды

Пересобрать и прогнать тесты:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from tests tests
```

Полностью очистить окружение:

```bash
docker compose down -v
```

Посмотреть логи Auth Service:

```bash
docker compose logs auth-service
```

Зайти в тестовую PostgreSQL базу:

```bash
docker compose exec auth-postgres \
  psql -U auth_user -d auth_test
```

Проверить таблицы:

```bash
docker compose exec auth-postgres \
  psql -U auth_user -d auth_test -c "\dt"
```
