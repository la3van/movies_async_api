# UGC Service

Production-like FastAPI-сервис пользовательского контента онлайн-кинотеатра. Сервис реализует CRUD закладок, оценок и рецензий, лайки/дизлайки рецензий и агрегированную статистику фильмов. Основное хранилище — MongoDB.

В общем Compose сервис называется `ugc-service`, использует MongoDB и Redis
DB 4, проверяет пользователей через `auth-service`, а фильмы — через
`content-service`. API доступен через Nginx, а собственная документация и
health endpoints — в пространстве `/ugc` той же точки входа.

## Возможности

- одна закладка на пару `user_id + film_id`;
- одна оценка от `0` до `10` на пару `user_id + film_id`;
- лайк фильма хранится как оценка `10`, дизлайк — как `0`;
- количество оценок, средняя оценка, число лайков/дизлайков и распределение `0..10`;
- одна рецензия пользователя на фильм;
- создание, чтение, изменение и удаление собственной рецензии;
- один изменяемый голос (`like` или `dislike`) пользователя на рецензию;
- сортировка рецензий по дате публикации, дате изменения, лайкам, дизлайкам, полезности и оценке фильма автором;
- проверка JWT и активного пользователя через существующий Auth Service;
- проверка существования фильма через Content Service с положительным Redis-кешем;
- уникальные и сортировочные MongoDB-индексы создаются при запуске;
- Redis rate limiting, `X-Request-ID`, единый формат ошибок, OpenTelemetry tracing;
- отдельные liveness `/health` и readiness `/ready` endpoints.

## Архитектура

Структура и разделение ответственности соответствуют `content_service`:

```text
src/
├── api/
│   ├── dependencies.py
│   ├── exception_handlers.py
│   ├── health.py
│   └── v1/
│       ├── endpoints/
│       ├── mappers/
│       ├── schemas/
│       └── router.py
├── auth/
├── cache/
├── core/
├── db/
├── integrations/
├── models/
├── repositories/
│   ├── interfaces/
│   └── mongo/
│       └── pipelines/
├── services/
└── main.py
```

HTTP-слой валидирует контракт и формирует ответы. Сервисный слой содержит бизнес-правила и проверки владения. Репозитории скрывают MongoDB и возвращают доменные Pydantic-модели. Aggregation pipelines вынесены отдельно.

## Коллекции MongoDB

| Коллекция | Назначение | Ключ уникальности |
|---|---|---|
| `bookmarks` | фильмы, отложенные пользователем | `user_id + film_id` |
| `ratings` | пользовательские оценки `0..10` | `user_id + film_id` |
| `reviews` | тексты рецензий и данные автора | `user_id + film_id` |
| `review_reactions` | лайки/дизлайки рецензий | `user_id + review_id` |

UUID сохраняются строками. Это делает документы и запросы прозрачными, не привязывает внешний контракт к BSON UUID representation и упрощает перенос данных.

## API

Все доменные endpoints требуют `Authorization: Bearer <access-token>`.

### Закладки

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/v1/bookmarks/` | список закладок |
| `GET` | `/api/v1/bookmarks/{film_id}` | одна закладка |
| `PUT` | `/api/v1/bookmarks/{film_id}` | идемпотентное добавление |
| `DELETE` | `/api/v1/bookmarks/{film_id}` | идемпотентное удаление |

### Оценки

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/v1/ratings/{film_id}` | оценка текущего пользователя |
| `PUT` | `/api/v1/ratings/{film_id}` | создание/изменение оценки |
| `DELETE` | `/api/v1/ratings/{film_id}` | удаление оценки |
| `GET` | `/api/v1/ratings/{film_id}/stats` | агрегаты фильма |

Тело `PUT`:

```json
{"value": 8}
```

### Рецензии

| Метод | URL | Назначение |
|---|---|---|
| `GET` | `/api/v1/reviews/films/{film_id}` | список рецензий фильма |
| `POST` | `/api/v1/reviews/films/{film_id}` | публикация рецензии |
| `GET` | `/api/v1/reviews/{review_id}` | одна рецензия |
| `PATCH` | `/api/v1/reviews/{review_id}` | изменение своей рецензии |
| `DELETE` | `/api/v1/reviews/{review_id}` | удаление своей рецензии |
| `GET` | `/api/v1/reviews/{review_id}/reaction` | свой голос |
| `PUT` | `/api/v1/reviews/{review_id}/reaction` | создать/заменить голос |
| `DELETE` | `/api/v1/reviews/{review_id}/reaction` | удалить голос |

Тело рецензии:

```json
{"text": "Сильный фильм с отличной операторской работой."}
```

Тело голоса:

```json
{"value": "like"}
```

Доступные значения `sort` для списка рецензий:

- `published_at`, `updated_at`, `likes`, `dislikes`, `helpfulness`, `author_rating`;
- префикс `-` меняет направление на убывание, например `-helpfulness`.

Сортировка по голосам и оценке автора выполняется MongoDB aggregation с `$lookup` в смежные коллекции, поэтому результат не зависит от фоновой денормализации счётчиков.

## Конфигурация

Скопируйте `.env.example` в `.env` и замените секреты. Критически важно задать `JWT_SECRET_KEY` тем же значением, что использует Auth Service.

`CONTENT_VALIDATE_FILMS=true` включает проверку `film_id` через Content Service. Для изолированной локальной разработки её можно временно отключить, но в интеграционном окружении значение должно оставаться `true`.

`AUTH_ALLOW_JWT_FALLBACK=true` повторяет отказоустойчивый подход `content_service`: если Auth Service недоступен, сервис принимает только локально проверенный, непросроченный access JWT. Ответы `401/403` от Auth Service никогда не обходятся fallback-механизмом.

## Запуск

В составе общей системы сервис ожидает доступные хосты `mongodb`, `redis`, `auth-service`, `content-service` и опционально Jaeger.

Для запуска приложения и хранилищ:

```bash
docker compose up --build
```

Доменные endpoints доступны через Nginx на `http://127.0.0.1:8000/api/v1`,
Swagger UI — на `http://127.0.0.1:8000/ugc/docs`. Проверки состояния:
`/ugc/health` и `/ugc/ready`.

Для запуска без Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Коды ошибок

Ожидаемые ошибки возвращаются в едином формате:

```json
{
  "detail": "review_not_found",
  "request_id": "4ae3a64239f348c9bf567af4d6cc8ccb"
}
```

Используются `401` для отсутствующего/невалидного токена, `403` для чужой рецензии, `404` для отсутствующего ресурса, `409` для повторной рецензии, `422` для ошибок валидации, `429` для превышения лимита и `503` для недоступной обязательной зависимости.
