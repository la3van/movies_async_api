# Мониторинг ошибок в Sentry

Sentry подключён ко всем Python-процессам проекта:

- Auth, Content и UGC Services — интеграция FastAPI;
- Events Service — интеграция Flask;
- Admin Service — интеграция Django;
- Content ETL и Events ETL — перехват необработанных исключений и ERROR-логов.

SDK не отправляет данные, пока `SENTRY_DSN` пуст. Поэтому локальная разработка
и CI продолжают работать без Sentry-аккаунта.

## Настройка

Создайте Sentry project и скопируйте его DSN в `.env` нужного сервиса:

```env
SENTRY_DSN=https://public-key@sentry.example/1
SENTRY_ENVIRONMENT=local
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_PROFILES_SAMPLE_RATE=0.0
```

Для production рекомендуется создать отдельный Sentry project и DSN для
каждого сервиса. Допустимо использовать один DSN: события всё равно получают
тег `service.name`, но отдельные проекты проще разграничивать и настраивать.

Значение DSN нельзя коммитить. Оно должно находиться только в локальных `.env`
или в secrets окружения развёртывания. После изменения переменных пересоздайте
контейнеры:

```bash
docker compose up -d --build --force-recreate
```

## Что отправляется

- необработанные исключения с stack trace;
- записи уровня `ERROR` и выше;
- HTTP-транзакции, если `SENTRY_TRACES_SAMPLE_RATE` больше нуля;
- профили, если включены и tracing, и `SENTRY_PROFILES_SAMPLE_RATE`.

По умолчанию tracing и profiling отключены, так как распределённые трассы уже
собираются OpenTelemetry и отображаются в Jaeger. `send_default_pii=False`
запрещает SDK автоматически отправлять персональные данные.

## Безопасная проверка

После настройки DSN можно отправить искусственное тестовое событие без
добавления аварийного endpoint в API:

```bash
docker compose exec -T auth-service python - <<'PY'
import sentry_sdk

from core.sentry import init_sentry

if not init_sentry(service_name="auth-service"):
    raise SystemExit("SENTRY_DSN is empty")

sentry_sdk.capture_message(
    "Local Sentry integration test",
    level="error",
)
sentry_sdk.flush(timeout=5)
PY
```

Событие должно появиться в Sentry с тегом
`service.name=auth-service` и environment `local`.

