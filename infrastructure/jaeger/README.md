# Jaeger и OpenTelemetry

Проект использует OpenTelemetry для создания distributed traces и Jaeger для их приёма, хранения и просмотра.

## Контур трассировки

```text
HTTP client
    ↓
Nginx
    ├── назначает или сохраняет X-Request-ID
    └── передаёт запрос backend-сервису
            ↓
    Content / Auth / Admin Service
    ├── framework server span
    ├── ручной business span
    ├── Redis / SQL / Elasticsearch / HTTPX child spans
    └── BatchSpanProcessor
            ↓ OTLP/gRPC
       jaeger:4317
            ↓
       Jaeger UI: 127.0.0.1:16686
```

Jaeger запускается корневым `docker-compose.yml` через образ `jaegertracing/all-in-one`.

| Интерфейс | Адрес |
| --- | --- |
| OTLP/gRPC внутри Docker-сети | `http://jaeger:4317` |
| Jaeger UI на хосте | `http://127.0.0.1:16686/` |

Jaeger all-in-one в текущем Compose не использует отдельный persistent volume. Локальные traces исчезают при пересоздании контейнера.

## Инструментированные сервисы

### Content Service

Автоматическая инструментация:

- FastAPI;
- Redis;
- Elasticsearch.

Ручные spans:

```text
content.films.get_by_id
content.films.get_sorted
content.films.search
content.films.get_similar
content.genres.get_by_id
content.genres.get_many
content.persons.get_by_id
content.persons.get_many
content.persons.get_films
```

### Auth Service

Автоматическая инструментация:

- FastAPI;
- Redis;
- SQLAlchemy для async PostgreSQL engine.

Ручные spans:

```text
auth.register
auth.login
auth.refresh
auth.logout
auth.logout_others
users.*
roles.*
permissions.*
tokens.create_access
tokens.create_refresh
tokens.create_pair
```

### Admin Service

Автоматическая инструментация:

- Django;
- HTTPX;
- psycopg.

Ручные spans:

```text
admin.authenticate
admin.get_user
```

`content-etl` пока не экспортирует OpenTelemetry traces.

## Настройка provider

Каждый HTTP-сервис создаёт собственный `TracerProvider`:

- `Resource` содержит `service.name`;
- `BatchSpanProcessor` отправляет завершённые spans пакетами;
- `OTLPSpanExporter` использует gRPC endpoint Jaeger;
- sampler локально равен `ALWAYS_ON`.

Provider создаётся один раз. Повторный вызов `configure_tracing()` возвращает уже настроенный экземпляр.

## Автоматические и ручные spans

Автоматическая инструментация показывает технические операции:

```text
HTTP request
Redis GET / SET
SQL SELECT / INSERT / UPDATE
Elasticsearch search
HTTPX client request
```

Декоратор `trace_method()` добавляет смысловую границу бизнес-метода:

```python
@trace_method("content.films.get_sorted")
async def get_sorted_films(...):
    ...
```

Во время выполнения метода созданный span является current span. Поэтому автоматически инструментированные вызовы внутри метода становятся его дочерними:

```text
GET /api/v1/films/
└── content.films.get_sorted
    ├── Redis GET
    ├── Elasticsearch search
    └── Redis SET
```

Декоратор отдельно обрабатывает `async def` и обычные `def`, чтобы span оставался открытым до фактического завершения coroutine или синхронной функции.

## Distributed context

### `traceparent`

`traceparent` — стандартный заголовок OpenTelemetry/W3C Trace Context. Он передаёт `trace_id`, parent span и sampling decision между сервисами.

В проекте `HTTPXClientInstrumentor` автоматически передаёт его при вызове:

```text
admin-service → auth-service
```

Поэтому один вход в Django Admin отображается как trace с двумя сервисами.

### `X-Request-ID`

Nginx сохраняет клиентский `X-Request-ID` или создаёт собственный `$request_id`. Значение:

- передаётся backend-сервису;
- возвращается клиенту;
- пишется в Nginx access log;
- захватывается OpenTelemetry в серверный span;
- вручную прокидывается Admin Service в запросы Auth Service `/auth/login` и `/users/me`.

Ожидаемый атрибут Jaeger:

```text
http.request.header.x_request_id = ["request-id-value"]
```

`X-Request-ID` не заменяет `trace_id`: первый нужен для корреляции с логами и внешним запросом, второй связывает spans OpenTelemetry.

## Переменные окружения

Одинаковый набор используется в `.env` и `.env.example` трёх HTTP-сервисов:

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=content-service
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_EXPORTER_OTLP_INSECURE=true
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST=x-request-id
```

| Переменная | Назначение |
| --- | --- |
| `OTEL_ENABLED` | Включает provider и instrumentors |
| `OTEL_SERVICE_NAME` | Значение `service.name` в Jaeger |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Адрес OTLP/gRPC collector |
| `OTEL_EXPORTER_OTLP_INSECURE` | Разрешает незашифрованный gRPC внутри локальной Docker-сети |
| `OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST` | Добавляет перечисленные входящие заголовки в server span attributes |

Для Admin и Auth Service значение `OTEL_SERVICE_NAME` должно быть соответственно `admin-service` и `auth-service`.

## Запуск

Запустить весь проект:

```bash
docker compose up -d --build
```

Запустить только Jaeger:

```bash
docker compose up -d jaeger
```

Проверить состояние:

```bash
docker compose ps jaeger content-service auth-service admin-service
```

Логи:

```bash
docker compose logs --tail=200 \
  jaeger \
  content-service \
  auth-service \
  admin-service
```

После изменения только `.env` достаточно пересоздать HTTP-сервисы:

```bash
docker compose up -d --force-recreate \
  content-service \
  auth-service \
  admin-service
```

После изменения Python-кода или `requirements.txt` требуется build:

```bash
docker compose up -d --build --force-recreate \
  content-service \
  auth-service \
  admin-service
```

## Проверка Content Service

Выполните запрос с явным request ID:

```bash
curl -i \
  -H "X-Request-ID: trace-content-001" \
  "http://127.0.0.1:8000/api/v1/films/?page_number=1&page_size=5"
```

В ответе должен присутствовать:

```text
X-Request-ID: trace-content-001
```

В Jaeger:

1. откройте `http://127.0.0.1:16686/`;
2. выберите `content-service`;
3. установите `Lookback: Last Hour`;
4. откройте последний `GET /api/v1/films/`;
5. проверьте вложенность ручного span, Redis и Elasticsearch;
6. проверьте `http.request.header.x_request_id` на серверном span.

Первый запрос после очистки кеша обычно выглядит так:

```text
GET /api/v1/films/
└── content.films.get_sorted
    ├── Redis GET
    ├── Elasticsearch search
    └── Redis SET
```

Повтор того же запроса:

```text
GET /api/v1/films/
└── content.films.get_sorted
    └── Redis GET
```

## Проверка Admin → Auth

1. Откройте `http://127.0.0.1:8000/admin/login/`.
2. Выполните успешный вход.
3. В Jaeger выберите `admin-service` и `POST /admin/login/`.
4. Проверьте, что trace содержит `admin-service` и `auth-service`.

Ожидаемая структура:

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

У серверного span Admin Service и серверных spans Auth Service для `/auth/login` и `/users/me` должен быть одинаковый `X-Request-ID`. Вызов `/auth/logout` остаётся частью того же trace через `traceparent`, но текущая реализация не передаёт в него `X-Request-ID`.

## Ошибочные запросы

Исключение, вышедшее за границы `start_as_current_span()`, записывается в span как error с exception event. Например, неуспешный вход создаёт более короткий trace и не содержит вызовов `/users/me` и `/auth/logout`.

В telemetry нельзя записывать:

- пароль;
- access- или refresh-token;
- password hash;
- cookie;
- полный Authorization header;
- персональные данные без необходимости.

## Диагностика

### Сервис не появился в Jaeger

Проверьте переменные внутри контейнера:

```bash
docker compose exec content-service env | grep '^OTEL_'
```

Проверьте логи на ошибки:

```text
Failed to export traces
StatusCode.UNAVAILABLE
Connection refused
```

Убедитесь, что endpoint равен `http://jaeger:4317`, а контейнер `jaeger` запущен.

### Есть HTTP-span, но нет Redis, SQL или Elasticsearch

Проверьте, что соответствующий instrumentor установлен и вызывается:

```text
RedisInstrumentor
ElasticsearchInstrumentor
SQLAlchemyInstrumentor
PsycopgInstrumentor
```

### Ручной span является соседним, а не родительским

Instrumented-вызов должен выполняться внутри декорированного метода. Для async-метода wrapper обязан вызывать оригинальную функцию через `await`.

### Нет `X-Request-ID` в span

Проверьте:

```env
OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST=x-request-id
```

и наличие `proxy_set_header X-Request-ID` в Nginx.

### Предупреждение о повторной регистрации provider

Сообщение:

```text
Overriding of current TracerProvider is not allowed
```

означает повторную настройку provider. `configure_tracing()` должен вызываться один раз на процесс и возвращать сохранённый provider при повторном обращении.

## Ограничения локальной конфигурации

- sampler `ALWAYS_ON` сохраняет 100% traces и подходит для разработки, но не для высоконагруженного production;
- Jaeger all-in-one не является production-кластером;
- traces не сохраняются после удаления или пересоздания контейнера Jaeger;
- Nginx-запросы, не дошедшие до backend, в Jaeger не отображаются;
- ручные spans следует добавлять вокруг значимых бизнес-операций, а не каждой вспомогательной функции.
