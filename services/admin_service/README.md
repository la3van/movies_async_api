# Admin Service

Django Admin для управления фильмами, жанрами и персонами онлайн-кинотеатра.

Сервис не содержит собственной базы контента. Он подключается к существующим таблицам схемы `content` в PostgreSQL `theatre-db`.

Аутентификация пользователей выполняется через отдельный `auth-service`.

В актуальном общем окружении сервис запускается как `admin-service`, получает
контент из `theatre-db`, проверяет учётные данные через `auth-service` и
доступен через Nginx по адресу `http://127.0.0.1:8000/admin/`. Docker-образ
использует Python 3.10, а CI дополнительно проверяет совместимость исходного
кода с Python 3.11 и 3.12.

## Возможности

- просмотр, создание, изменение и удаление фильмов и сериалов;
- управление жанрами;
- управление персонами;
- назначение жанров фильму через inline-формы;
- назначение актёров, режиссёров и сценаристов;
- поиск по названию, описанию и UUID;
- фильтрация по типу, жанру и дате;
- сортировка и постраничный вывод;
- авторизация через `auth-service`;
- доступ только активным суперпользователям;
- локальная Django-сессия после успешного входа;
- журнал действий Django Admin;
- опциональная Django Debug Toolbar.

## Стек

- Python 3.10;
- Django 5.0;
- Gunicorn;
- HTTPX;
- psycopg 3;
- SQLite;
- PostgreSQL;
- WhiteNoise;
- Django Debug Toolbar;
- OpenTelemetry SDK и OTLP/gRPC exporter;
- Jaeger.

## Архитектура

```text
Browser
   │
   ▼
Nginx
   │ /admin/, /static/, /__debug__/
   ▼
Admin Service
   ├── internal HTTP → Auth Service
   │                    ├── проверка логина и пароля
   │                    └── получение текущего пользователя
   │
   ├── SQLite
   │   ├── shadow users
   │   ├── Django sessions
   │   ├── admin log
   │   ├── permissions
   │   └── migration history
   │
   └── PostgreSQL theatre
       └── schema content
           ├── film_work
           ├── genre
           ├── person
           ├── genre_film_work
           └── person_film_work

Admin Service ── OTLP/gRPC ──► Jaeger
```

С хоста Admin Service доступен только через Nginx. Внутреннее обращение к Auth Service выполняется напрямую по адресу `auth-service:8000`, без повторного прохождения через Nginx.

## Структура

```text
admin_service/
├── admin_auth/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   └── backends.py
├── admin_panel/
│   ├── __init__.py
│   ├── asgi.py
│   ├── debug_toolbar.py
│   ├── settings.py
│   ├── tracing.py
│   ├── urls.py
│   └── wsgi.py
├── content/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   └── router.py
├── .dockerignore
├── .env.example
├── Dockerfile
├── entrypoint.sh
├── manage.py
├── requirements.txt
└── README.md
```

## Пакеты приложения

### `admin_panel`

Основной Django-проект.

Содержит:

- глобальные настройки;
- подключения к SQLite и PostgreSQL;
- URL Django Admin;
- WSGI- и ASGI-точки входа;
- настройку Debug Toolbar;
- подключение authentication backend;
- подключение database router.

### `admin_auth`

Интеграция Django с `auth-service`.

`AuthServiceBackend`:

1. получает логин и пароль из стандартной формы Django Admin;
2. отправляет их в `POST /api/v1/auth/login`;
3. получает access- и refresh-токены;
4. запрашивает `GET /api/v1/users/me`;
5. проверяет `is_active` и `is_superuser`;
6. создаёт или обновляет локального shadow-пользователя;
7. отключает локальный пароль через `set_unusable_password()`;
8. возвращает пользователя Django для создания сессии;
9. пытается отозвать временную refresh-сессию через `/api/v1/auth/logout`.

Настоящий пароль пользователя хранится только в базе Auth Service.

Локальный shadow-пользователь нужен для:

- `request.user`;
- Django-сессии;
- проверки `is_staff` и `is_superuser`;
- журнала действий `django_admin_log`.

### `content`

Описывает существующие таблицы контента через Django ORM.

Модели:

- `FilmWork`;
- `Genre`;
- `Person`;
- `GenreFilmWork`;
- `PersonFilmWork`.

Актёр, режиссёр и сценарист представлены одной моделью `Person`, а роль хранится в `PersonFilmWork.role`.

У конкретных контентных моделей указано:

```python
managed = False
```

Django может читать и изменять записи, но не создаёт, не удаляет и не изменяет структуру этих таблиц через migrations.

`ContentDatabaseRouter` направляет чтение и запись моделей приложения `content` в PostgreSQL-подключение с alias `content`.

Остальные Django-модели используют SQLite-подключение `default`.

## Базы данных

### SQLite — `default`

Путь задаётся переменной:

```env
SQLITE_PATH=/app/data/admin.sqlite3
```

SQLite хранит только служебные данные Django:

- локальных shadow-пользователей;
- сессии;
- permissions;
- группы;
- журнал действий;
- историю миграций.

Настоящие пользовательские пароли в SQLite не сохраняются.

Файл базы должен сохраняться через named volume:

```yaml
volumes:
  - admin_service_data:/app/data
```

### PostgreSQL — `content`

Admin Service подключается к существующей базе:

```text
host: theatre-db
database: theatre
schema: content
```

Основные таблицы:

```text
content.film_work
content.genre
content.person
content.genre_film_work
content.person_film_work
```

Django migrations для этого подключения запрещены database router.

## Авторизация

В `settings.py` используется только кастомный backend:

```python
AUTHENTICATION_BACKENDS = [
    "admin_auth.backends.AuthServiceBackend",
]
```

Стандартный `ModelBackend` Django не используется.

Для входа пользователь должен иметь в Auth Service:

```text
is_active = true
is_superuser = true
```

После успешной проверки создаётся локальный shadow-пользователь:

```text
username      = login из Auth Service
email         = email из Auth Service
first_name    = first_name из Auth Service
last_name     = last_name из Auth Service
is_active     = true
is_staff      = true
is_superuser  = true
password      = unusable
```

Пароль, введённый в форме Django Admin, передаётся в Auth Service только для проверки и не сохраняется в SQLite.

После входа дальнейшие запросы используют локальную Django-сессию. Auth Service повторно проверяется при следующем входе после завершения или удаления сессии.

## Переменные окружения

Создайте локальный `.env`:

```bash
cp services/admin_service/.env.example \
   services/admin_service/.env
```

### Основные настройки

| Переменная | Назначение |
| --- | --- |
| `PROJECT_NAME` | Название сервиса и заголовок Django Admin |
| `DEBUG` | Режим отладки Django |
| `ENABLE_DEBUG_TOOLBAR` | Дополнительный флаг Django Debug Toolbar |
| `SECRET_KEY` | Секрет подписи внутренних данных Django |
| `ALLOWED_HOSTS` | Разрешённые значения заголовка Host |
| `CSRF_TRUSTED_ORIGINS` | Доверенные origins Nginx для CSRF-защиты, локально `http://localhost:8000` и `http://127.0.0.1:8000` |
| `LANGUAGE_CODE` | Язык интерфейса Django |
| `TIME_ZONE` | Часовой пояс Django |

### Admin Service и SQLite

| Переменная | Назначение |
| --- | --- |
| `ADMIN_SERVICE_HOST` | Адрес Gunicorn внутри контейнера |
| `ADMIN_SERVICE_PORT` | Порт Gunicorn внутри контейнера |
| `SQLITE_PATH` | Путь к служебной SQLite-базе |
| `SESSION_COOKIE_AGE` | Срок жизни Django-сессии в секундах |
| `GUNICORN_WORKERS` | Количество worker-процессов Gunicorn |
| `GUNICORN_TIMEOUT` | Таймаут обработки запроса Gunicorn |

### PostgreSQL

| Переменная | Назначение |
| --- | --- |
| `POSTGRES_HOST` | Docker hostname PostgreSQL |
| `POSTGRES_PORT` | Порт PostgreSQL |
| `POSTGRES_DB` | Имя базы контента |
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `POSTGRES_OPTIONS` | Дополнительные параметры соединения, включая `search_path` |
| `POSTGRES_CONNECT_TIMEOUT` | Таймаут подключения к PostgreSQL |
| `POSTGRES_STATEMENT_TIMEOUT_MS` | Максимальное время SQL-запроса |

### Auth Service

| Переменная | Назначение |
| --- | --- |
| `AUTH_SERVICE_HOST` | Docker hostname Auth Service |
| `AUTH_SERVICE_PORT` | Внутренний порт Auth Service |
| `AUTH_SERVICE_API_PREFIX` | Префикс API Auth Service |
| `AUTH_SERVICE_CONNECT_TIMEOUT` | Таймаут подключения к Auth Service |
| `AUTH_SERVICE_READ_TIMEOUT` | Таймаут ожидания ответа Auth Service |

### OpenTelemetry

| Переменная | Назначение |
| --- | --- |
| `OTEL_ENABLED` | Включает настройку provider и instrumentors |
| `OTEL_SERVICE_NAME` | Имя сервиса в Jaeger, локально `admin-service` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP/gRPC endpoint, локально `http://jaeger:4317` |
| `OTEL_EXPORTER_OTLP_INSECURE` | Использование незашифрованного gRPC внутри Docker-сети |
| `OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST` | Список входящих заголовков для span attributes, локально `x-request-id` |

## Распределённая трассировка

`configure_tracing()` вызывается в `admin_panel/wsgi.py` и `admin_panel/asgi.py` до создания Django application.

Автоматически подключаются:

| Instrumentor | Что отображается в Jaeger |
| --- | --- |
| `DjangoInstrumentor` | серверные Django HTTP-spans |
| `HTTPXClientInstrumentor` | запросы `admin-service → auth-service` и передача `traceparent` |
| `PsycopgInstrumentor` | SQL-запросы к PostgreSQL theatre |

Authentication backend содержит ручные spans:

```text
admin.authenticate
admin.get_user
```

Ожидаемый distributed trace успешного входа:

```text
admin-service: POST /admin/login/
└── admin.authenticate
    ├── HTTPX POST /api/v1/auth/login
    │   └── auth-service: POST /api/v1/auth/login
    │       └── auth.login
    ├── HTTPX GET /api/v1/users/me
    │   └── auth-service: GET /api/v1/users/me
    └── HTTPX POST /api/v1/auth/logout
        └── auth-service: POST /api/v1/auth/logout
```

`AuthServiceBackend._build_headers()` дополнительно передаёт входящий `X-Request-ID` в запросы `/auth/login` и `/users/me`. Поэтому соответствующие серверные spans Admin Service и Auth Service можно сопоставить по одному значению `http.request.header.x_request_id`. Вспомогательный вызов `/auth/logout` сейчас не получает этот прикладной заголовок.

`traceparent` передаётся OpenTelemetry-инструментацией автоматически и объединяет все три HTTPX-вызова в один `trace_id`, включая `/auth/logout`. `X-Request-ID` используется отдельно для корреляции с Nginx access log.

Проверка:

1. Откройте `http://127.0.0.1:8000/admin/login/`.
2. Выполните успешный вход.
3. Откройте `http://127.0.0.1:16686/`.
4. Выберите `admin-service` и операцию `POST /admin/login/`.
5. Убедитесь, что trace содержит два сервиса: `admin-service` и `auth-service`.

Общие сведения и диагностика: [../../infrastructure/jaeger/README.md](../../infrastructure/jaeger/README.md).

## Генерация Django `SECRET_KEY`

Создайте отдельный ключ для Admin Service:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Поместите результат только в:

```text
services/admin_service/.env
```

В `.env.example` должно оставаться нейтральное значение:

```env
SECRET_KEY=generate_me
```

## Запуск

Для доступа из браузера запустите Nginx и его зависимости из корня репозитория:

```bash
docker compose up --build nginx
```

Запуск в фоне:

```bash
docker compose up -d --build nginx
```

Nginx автоматически поднимет `admin-service`, `auth-service`, `content-service` и необходимые инфраструктурные зависимости.

Админка доступна по адресу:

```text
http://127.0.0.1:8000/admin/
```

Прямой запуск:

```bash
docker compose up --build admin-service
```

поднимает Admin Service и его зависимости только внутри Docker-сети. Порт Admin Service на хост не публикуется.

## Создание суперпользователя

Admin Service не создаёт отдельного Django-суперпользователя.

Настройте данные суперпользователя в:

```text
services/auth_service/.env
```

Затем выполните:

```bash
docker compose exec auth-service \
  python -m src.commands.create_superuser
```

Для входа в Django Admin используйте логин и пароль этого пользователя.

## Запуск контейнера

Dockerfile запускает:

```text
sh /app/entrypoint.sh
```

`entrypoint.sh` последовательно выполняет:

1. служебные миграции Django в SQLite;
2. сбор статических файлов;
3. запуск Gunicorn.

Эквивалентные основные команды:

```bash
python manage.py migrate --database=default --noinput
python manage.py collectstatic --noinput
gunicorn admin_panel.wsgi:application
```

Миграции не изменяют таблицы `content.*` благодаря `managed=False` и `ContentDatabaseRouter`.

## Debug Toolbar

Toolbar включается только при одновременном выполнении двух условий:

```env
DEBUG=true
ENABLE_DEBUG_TOOLBAR=true
```

При любом другом сочетании панель отключена.

Служебные URL toolbar доступны внутри приложения по пути:

```text
/__debug__/
```

Открывать этот адрес отдельно обычно не требуется: панель встраивается в HTML-страницы Django Admin.

## Команды разработки

Проверить конфигурацию:

```bash
docker compose run --rm admin-service \
  python manage.py check
```

Проверить служебные миграции:

```bash
docker compose run --rm admin-service \
  python manage.py showmigrations
```

Открыть Django shell:

```bash
docker compose exec admin-service \
  python manage.py shell
```

Повторно собрать статику:

```bash
docker compose exec admin-service \
  python manage.py collectstatic --noinput
```

Посмотреть логи Admin Service и reverse proxy:

```bash
docker compose logs -f admin-service nginx jaeger
```

Пересобрать образ после изменения зависимостей:

```bash
docker compose build --no-cache admin-service
```

## Проверка интеграции

1. Запустите `docker compose up -d --build nginx content-etl`.
2. Создайте суперпользователя в Auth Service.
3. Откройте `http://127.0.0.1:8000/admin/`.
4. Войдите с учётными данными Auth Service.
5. Откройте список фильмов, жанров или персон.
6. Измените тестовую запись.
7. Проверьте изменение данных в PostgreSQL.
8. После работы ETL проверьте обновление соответствующего документа в Elasticsearch.

## Важные ограничения

- Auth Service является единственным источником истины для пользователей и паролей.
- SQLite содержит только техническую копию пользователя и Django-сессию.
- Структура таблиц `content.*` не управляется миграциями Admin Service.
- Изменение структуры контентной базы требует отдельного обновления инфраструктуры и последующего обновления Django-моделей.
- Доступ к Admin Service разрешён только активным суперпользователям Auth Service.

## Логи и Sentry

Логи контейнера автоматически поступают в общий ELK-стек и доступны в
Kibana по фильтру `service.name: "admin-service"`. Для отправки Django-ошибок
в Sentry задайте `SENTRY_DSN` в `.env`. Остальные Sentry-параметры и безопасная
проверка описаны в
[`../../infrastructure/sentry/README.md`](../../infrastructure/sentry/README.md).