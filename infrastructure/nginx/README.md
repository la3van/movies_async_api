# Nginx

Nginx является единой внешней точкой входа для прикладных HTTP-сервисов проекта.

Для доступа к прикладным HTTP-сервисам с хоста используется адрес:

```text
http://127.0.0.1:8000
```

Все прикладные сервисы доступны через внутреннюю Docker-сеть и не публикуют
собственные HTTP-порты на хост. Nginx разводит пересекающиеся служебные пути
по отдельным внешним адресам.

## Назначение

Nginx выполняет роль reverse proxy:

```text
HTTP client
    ↓
Nginx
    ├── Content Service
    ├── Auth Service
    ├── Admin Service
    ├── Events Service
    └── UGC Service
```

Он:

- выбирает backend по URL;
- сохраняет исходный URI запроса;
- передаёт proxy-заголовки;
- назначает или сохраняет `X-Request-ID`;
- пишет общий access log с адресом и временем ответа upstream;
- возвращает неизвестным маршрутам `404`.

## Файлы

```text
infrastructure/nginx/
├── nginx.conf
└── README.md
```

Отдельные `Dockerfile`, `.env` и зависимости не нужны. Корневой Compose использует официальный образ `nginx:alpine` и монтирует `nginx.conf` read-only.

## Маршрутизация

| Внешний путь | Backend | Внутренний путь |
| --- | --- | --- |
| `/api/v1/films/*` | `content-service:8000` | без изменения |
| `/api/v1/genres/*` | `content-service:8000` | без изменения |
| `/api/v1/persons/*` | `content-service:8000` | без изменения |
| `/api/openapi*` | `content-service:8000` | без изменения |
| `/api/redoc` | `content-service:8000` | `/redoc` |
| `/api/v1/auth/*` | `auth-service:8000` | без изменения |
| `/api/v1/users/*` | `auth-service:8000` | без изменения |
| `/api/v1/roles/*` | `auth-service:8000` | без изменения |
| `/api/v1/permissions/*` | `auth-service:8000` | без изменения |
| `/docs` | `auth-service:8000` | без изменения |
| `/openapi.json` | `auth-service:8000` | без изменения |
| `/redoc` | `auth-service:8000` | без изменения |
| `/health` | `auth-service:8000` | без изменения |
| `/api/v1/events` | `events-service:8000` | без изменения |
| `/api/v1/bookmarks/*` | `ugc-service:8000` | без изменения |
| `/api/v1/ratings/*` | `ugc-service:8000` | без изменения |
| `/api/v1/reviews/*` | `ugc-service:8000` | без изменения |
| `/ugc/docs` | `ugc-service:8000` | без изменения |
| `/ugc/openapi.json` | `ugc-service:8000` | без изменения |
| `/ugc/redoc` | `ugc-service:8000` | без изменения |
| `/ugc/health` | `ugc-service:8000` | `/health` |
| `/ugc/ready` | `ugc-service:8000` | `/ready` |
| `/admin/*` | `admin-service:8000` | без изменения |
| `/static/*` | `admin-service:8000` | без изменения |
| `/__debug__/*` | `admin-service:8000` | без изменения |

Запрос к `/` получает временный redirect `302` на `/api/openapi`. Запрос к `/admin` получает redirect `301` на `/admin/`.

Auth-маршруты описаны регулярным выражением и имеют приоритет над общим content-location `/api/`.

## Upstream-сервисы

```nginx
upstream content_service {
    server content-service:8000;
}

upstream auth_service {
    server auth-service:8000;
}

upstream admin_service {
    server admin-service:8000;
}

upstream events_service {
    server events-service:8000;
}

upstream ugc_service {
    server ugc-service:8000;
}
```

Имена upstream-сервисов разрешает внутренний DNS Docker Compose.

## Proxy-заголовки

Во все backend-сервисы передаются:

```text
Host
X-Real-IP
X-Forwarded-For
X-Forwarded-Host
X-Forwarded-Proto
X-Request-ID
```

Если клиент уже передал `X-Request-ID`, Nginx сохраняет его. Иначе используется автоматически созданный `$request_id`. Этот же идентификатор добавляется в ответ клиенту.

## Связь с распределённой трассировкой

Nginx не инструментирован OpenTelemetry и сам не создаёт spans. Его задача в observability-контуре — передать стабильный `X-Request-ID`:

```text
client request
    ↓
Nginx: сохранить клиентский X-Request-ID
       или создать $request_id
    ↓
backend server span:
http.request.header.x_request_id = ["..."]
```

`X-Request-ID` и OpenTelemetry `trace_id` решают разные задачи:

| Идентификатор | Назначение |
| --- | --- |
| `X-Request-ID` | Сопоставление Nginx access log, ответа клиенту и серверного span |
| `trace_id` | Объединение всех spans одного distributed trace |
| `traceparent` | Передача OpenTelemetry-контекста между сервисами |

Nginx передаёт `X-Request-ID`, но не формирует `traceparent`. Заголовок `traceparent` автоматически добавляется клиентской OpenTelemetry-инструментацией, например при HTTPX-вызове `admin-service → auth-service`.

Запрос, отклонённый самим Nginx, не попадёт в Jaeger, потому что backend не будет вызван. Такой запрос нужно искать в Nginx access log по `X-Request-ID`.

Проверка:

```bash
curl -i \
  -H "X-Request-ID: nginx-trace-check-001" \
  http://127.0.0.1:8000/api/v1/films/
```

В ответе должен присутствовать тот же `X-Request-ID`, а в Jaeger — атрибут серверного span:

```text
http.request.header.x_request_id = ["nginx-trace-check-001"]
```

Полная документация трассировки: [../jaeger/README.md](../jaeger/README.md).

## Запуск

Из корня репозитория:

```bash
docker compose up --build nginx
```

Запуск в фоне:

```bash
docker compose up -d --build nginx
```

Nginx запускает через `depends_on` все HTTP-сервисы и их инфраструктурные зависимости. Фоновый `content-etl` не входит в зависимости Nginx и запускается отдельно либо вместе со всем проектом:

```bash
docker compose up -d --build
```

## Проверка конфигурации

Проверить итоговый Compose:

```bash
docker compose config
```

Проверить синтаксис Nginx внутри запущенного контейнера:

```bash
docker compose exec nginx nginx -t
```

После изменения смонтированного `nginx.conf` можно пересоздать контейнер:

```bash
docker compose up -d --force-recreate nginx
```

## Проверка маршрутов

```bash
curl -I http://127.0.0.1:8000/
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/api/openapi.json
curl -i http://127.0.0.1:8000/ugc/health
curl -i http://127.0.0.1:8000/ugc/ready
curl -I http://127.0.0.1:8000/admin/
```

Основные адреса в браузере:

```text
Content Swagger: http://127.0.0.1:8000/api/openapi
Auth Swagger:    http://127.0.0.1:8000/docs
UGC Swagger:     http://127.0.0.1:8000/ugc/docs
Django Admin:    http://127.0.0.1:8000/admin/
```

## Логи

```bash
docker compose logs -f nginx
```

Access log содержит:

- URL и HTTP-метод;
- итоговый status;
- адрес upstream;
- status upstream;
- полное время запроса;
- время ответа backend;
- `X-Request-ID`.

По этому значению запрос можно сопоставить с серверным span в Jaeger.

## Типичные ошибки

### `502 Bad Gateway`

Nginx не может подключиться к backend или backend ещё запускается.

```bash
docker compose ps -a
docker compose logs --tail=200 \
  nginx \
  content-service \
  auth-service \
  admin-service \
  events-service \
  ugc-service
```

### Django возвращает `403 CSRF verification failed`

Проверьте в `services/admin_service/.env`:

```env
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

### Прямые адреса сервисов не открываются

Это ожидаемое поведение для всех прикладных сервисов. Используйте их маршруты
через Nginx на `127.0.0.1:8000`.