# Ревью поддерживаемости проекта `movies_async_api`

## 1. Цель ревью

Цель ревью — оценить поддерживаемость Python-кода проекта с помощью автоматической метрики **Maintainability Index**.

Для анализа использован инструмент **Radon**. После реорганизации репозитория отдельно проверены:

1. Content Service;
2. функциональные тесты Content Service;
3. Content ETL;
4. Auth Service;
5. функциональные тесты Auth Service;
6. миграции Alembic Auth Service.

Такое разделение позволяет не смешивать продуктовый код, инфраструктурную ETL-логику, миграции и тестовые сценарии.

---

## 2. Методика анализа

Анализ выполнялся из корневой директории проекта:

```bash
radon mi services/content_service -s
radon mi services/content_etl -s
radon mi services/auth_service -s
```

Флаг `-s` выводит буквенную категорию и точное числовое значение Maintainability Index.

Для интерпретации результатов использовалась шкала Radon:

| Значение MI | Категория | Интерпретация |
|---:|:---:|---|
| 20–100 | A | высокая поддерживаемость |
| 10–19 | B | средняя поддерживаемость |
| 0–9 | C | низкая поддерживаемость |

Категория `A` охватывает широкий диапазон значений, поэтому при сравнении файлов учитывалось и точное числовое значение.

Maintainability Index является ориентиром, а не абсолютной оценкой качества. Более низкое значение не доказывает наличие дефекта, но помогает выделить файлы для дополнительного ручного анализа.

---

## 3. Общий результат

Проверено **226 Python-файлов**:

| Часть проекта | Количество файлов | Минимальный MI | Файл с минимальным MI | Категория |
|---|---:|---:|---|:---:|
| Content Service | 51 | 55.89 | `services/content_service/src/api/v1/schemas/films.py` | A |
| Тесты Content Service | 32 | 26.33 | `services/content_service/tests/functional/src/films/test_film_similar.py` | A |
| Content ETL | 34 | 32.72 | `services/content_etl/postgres_to_es/sources/postgres.py` | A |
| Auth Service | 66 | 33.44 | `services/auth_service/src/services/auth.py` | A |
| Тесты Auth Service | 41 | 21.15 | `services/auth_service/tests/functional/src/permissions/test_update_permission.py` | A |
| Alembic Auth Service | 2 | 72.94 | `services/auth_service/alembic/env.py` | A |

Все проверенные файлы получили категорию `A`. Значений категорий `B` и `C` не обнаружено.

Минимальный показатель во всём проекте:

```text
services/auth_service/tests/functional/src/permissions/test_update_permission.py — A (21.15)
```

---

## 4. Content Service

### 4.1. Команда

```bash
radon mi services/content_service -s
```

В область проверки вошли как исходный код сервиса, так и его функциональные тесты.

### 4.2. Исходный код

Проверено **51 файла**. Минимальный показатель исходного кода Content Service — **55.89**.

Файлы с наиболее низким MI:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/content_service/src/api/v1/schemas/films.py` | 55.89 | A |
| `services/content_service/src/cache/redis.py` | 57.52 | A |
| `services/content_service/src/repositories/elastic/bodies/persons.py` | 58.97 | A |
| `services/content_service/src/services/film.py` | 60.57 | A |
| `services/content_service/src/db/redis.py` | 60.77 | A |
| `services/content_service/src/repositories/elastic/bodies/films.py` | 61.63 | A |
| `services/content_service/src/db/elastic.py` | 61.98 | A |
| `services/content_service/src/services/person.py` | 62.51 | A |
| `services/content_service/src/repositories/elastic/bodies/genres.py` | 64.28 | A |
| `services/content_service/src/services/genre.py` | 68.47 | A |

Все модули Content Service находятся в категории `A`. Наиболее низкие значения сосредоточены в схемах данных, Redis-инфраструктуре, сервисах и Elasticsearch-запросах. Это ожидаемо: такие файлы содержат больше прикладной или инфраструктурной логики, чем небольшие интерфейсы и декларативные модели.

Обязательный рефакторинг по результатам MI не требуется.

### 4.3. Функциональные тесты Content Service

Проверено **32 файла**. Минимальный показатель — **26.33**.

Файлы с наиболее низким MI:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/content_service/tests/functional/src/films/test_film_similar.py` | 26.33 | A |
| `services/content_service/tests/functional/src/persons/test_person_films.py` | 29.07 | A |
| `services/content_service/tests/functional/src/films/test_film_search.py` | 34.47 | A |
| `services/content_service/tests/functional/src/films/test_film_list.py` | 38.33 | A |
| `services/content_service/tests/functional/src/films/test_film_detail.py` | 41.10 | A |
| `services/content_service/tests/functional/test_data/films.py` | 43.29 | A |
| `services/content_service/tests/functional/src/genres/test_genre_list.py` | 45.42 | A |
| `services/content_service/tests/functional/src/persons/test_person_search.py` | 45.61 | A |
| `services/content_service/tests/functional/src/genres/test_genre_detail.py` | 46.58 | A |
| `services/content_service/tests/functional/src/persons/test_person_detail.py` | 46.84 | A |

Самый низкий показатель имеет тест похожих фильмов. Снижение MI в тестовых модулях объясняется количеством сценариев, подготовкой данных, параметризацией и большим числом проверок. При этом все тестовые файлы остаются в категории высокой поддерживаемости.

---

## 5. Content ETL

### 5.1. Команда

```bash
radon mi services/content_etl -s
```

Проверено **34 файла**. Минимальный показатель — **32.72**.

Файлы с наиболее низким MI:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/content_etl/postgres_to_es/sources/postgres.py` | 32.72 | A |
| `services/content_etl/postgres_to_es/loaders/elastic.py` | 40.83 | A |
| `services/content_etl/postgres_to_es/models/postgres_models.py` | 52.29 | A |
| `services/content_etl/postgres_to_es/transforms/persons.py` | 53.02 | A |
| `services/content_etl/postgres_to_es/backoff.py` | 53.05 | A |
| `services/content_etl/postgres_to_es/pipelines/films.py` | 53.57 | A |
| `services/content_etl/postgres_to_es/state/redis.py` | 55.72 | A |
| `services/content_etl/postgres_to_es/pipelines/base.py` | 55.86 | A |
| `services/content_etl/postgres_to_es/bootstrap.py` | 55.87 | A |
| `services/content_etl/postgres_to_es/pipelines/persons.py` | 56.39 | A |
| `services/content_etl/postgres_to_es/service.py` | 56.74 | A |
| `services/content_etl/postgres_to_es/transforms/movies.py` | 58.35 | A |

Наиболее низкий индекс имеет PostgreSQL-источник данных:

```text
services/content_etl/postgres_to_es/sources/postgres.py — A (32.72)
```

Следом идёт Elasticsearch loader:

```text
services/content_etl/postgres_to_es/loaders/elastic.py — A (40.83)
```

Эти модули содержат работу с внешними хранилищами, пакетную обработку, циклы, повторные попытки и обработку ошибок. Такая концентрация инфраструктурной логики закономерно снижает числовое значение MI.

Оба файла остаются в категории `A`. Декомпозиция только ради увеличения метрики не требуется. При дальнейшем развитии проекта стоит следить за тем, чтобы в этих модулях не смешивались формирование запросов, управление соединениями, преобразование данных и обработка повторных попыток.

---

## 6. Auth Service

### 6.1. Команда

```bash
radon mi services/auth_service -s
```

В область проверки вошли исходный код, функциональные тесты и миграции Alembic.

### 6.2. Исходный код

Проверено **66 файлов**. Минимальный показатель — **33.44**.

Файлы с наиболее низким MI:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/auth_service/src/services/auth.py` | 33.44 | A |
| `services/auth_service/src/services/role.py` | 34.14 | A |
| `services/auth_service/src/services/user.py` | 35.46 | A |
| `services/auth_service/src/services/permission.py` | 38.82 | A |
| `services/auth_service/src/api/dependencies.py` | 47.40 | A |
| `services/auth_service/src/commands/create_superuser.py` | 51.31 | A |
| `services/auth_service/src/cache/redis.py` | 52.46 | A |
| `services/auth_service/src/api/v1/schemas/users.py` | 56.45 | A |
| `services/auth_service/src/api/v1/schemas/roles.py` | 56.54 | A |
| `services/auth_service/src/models/login_history.py` | 57.37 | A |
| `services/auth_service/src/services/token.py` | 57.71 | A |
| `services/auth_service/src/db/postgres.py` | 58.43 | A |

Минимальные значения имеют сервисы авторизации, ролей, пользователей и разрешений. Это наиболее насыщенные бизнес-логикой модули Auth Service: они объединяют транзакции, работу с репозиториями, проверку ошибок, кеширование и каскадную инвалидацию зависимых кешей.

Даже минимальное значение `33.44` остаётся заметно выше нижней границы категории `A`.

### 6.3. Функциональные тесты Auth Service

Проверено **41 файл**. Минимальный показатель — **21.15**.

Файлы с наиболее низким MI:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/auth_service/tests/functional/src/permissions/test_update_permission.py` | 21.15 | A |
| `services/auth_service/tests/functional/src/roles/test_update_role.py` | 25.82 | A |
| `services/auth_service/tests/functional/src/users/test_user_roles.py` | 29.54 | A |
| `services/auth_service/tests/functional/src/permissions/test_get_permissions.py` | 30.26 | A |
| `services/auth_service/tests/functional/src/users/test_login_history.py` | 30.81 | A |
| `services/auth_service/tests/functional/src/roles/test_get_roles.py` | 31.48 | A |
| `services/auth_service/tests/functional/src/auth/test_register.py` | 35.26 | A |
| `services/auth_service/tests/functional/fixtures/auth.py` | 35.89 | A |
| `services/auth_service/tests/functional/src/permissions/test_create_permission.py` | 36.11 | A |
| `services/auth_service/tests/functional/src/roles/test_create_role.py` | 36.79 | A |
| `services/auth_service/tests/functional/src/roles/test_delete_role.py` | 36.91 | A |
| `services/auth_service/tests/functional/src/auth/test_login.py` | 37.62 | A |
| `services/auth_service/tests/functional/src/users/test_update_user.py` | 38.22 | A |
| `services/auth_service/tests/functional/src/auth/test_refresh.py` | 38.48 | A |
| `services/auth_service/tests/functional/src/auth/test_logout.py` | 38.92 | A |

Минимальный показатель всего проекта относится к:

```text
services/auth_service/tests/functional/src/permissions/test_update_permission.py — A (21.15)
```

Файл остаётся в категории `A`, но находится близко к её нижней границе. Причина — большое количество сценариев обновления:

- полное и частичное обновление;
- очистка nullable-полей;
- дублирование кода;
- отсутствие сущности;
- проверки прав доступа;
- невалидные path- и body-параметры;
- проверка инвалидации item-, list- и зависимых кешей.

Тесты Auth Service разделены по endpoint и типу операции. Это улучшает навигацию по сравнению с крупными монолитными тестовыми файлами. Дополнительное сокращение параметризации или объединение сценариев возможно отдельным рефакторингом, но по текущему MI обязательным не является.

### 6.4. Миграции Alembic

Проверено **2 файла**:

| Файл | MI | Категория |
|---|---:|:---:|
| `services/auth_service/alembic/env.py` | 72.94 | A |
| `services/auth_service/alembic/versions/063da50fd6fc_create_auth_tables.py` | 100.00 | A |

Оба файла имеют категорию `A`. Миграция таблиц является преимущественно декларативной, поэтому значение `100.00` не требует отдельной интерпретации.

---

## 7. Сравнение частей проекта

| Часть проекта | Минимальный MI | Итоговая категория |
|---|---:|:---:|
| Content Service | 55.89 | A |
| Content ETL | 32.72 | A |
| Auth Service | 33.44 | A |
| Функциональные тесты Content Service | 26.33 | A |
| Функциональные тесты Auth Service | 21.15 | A |

Более низкие значения тестовых модулей не означают, что тесты написаны хуже продуктового кода. На MI влияют объём файла, количество ветвлений, число выражений и комментариев. Функциональные тесты естественным образом содержат большое количество сценариев, проверок и подготовительных действий.

Файлы со значением `100.00` в основном являются пустыми `__init__.py`, небольшими интерфейсами или декларативными модулями. Поэтому их результат не следует сравнивать напрямую с полноценными сервисами.

---

## 8. Общие выводы

1. Все **226** проверенных Python-файла получили категорию `A`.
2. Файлов категорий `B` и `C` не обнаружено.
3. Минимальный MI продуктового кода равен `32.72` и относится к PostgreSQL-источнику ETL.
4. Минимальный MI Auth Service равен `33.44` и относится к `services/auth_service/src/services/auth.py`.
5. Минимальный MI тестового кода равен `21.15` и относится к тестам обновления permissions.
6. Content Service имеет наиболее высокие минимальные показатели среди продуктовых сервисов.
7. Более низкие значения ETL и Auth Service объясняются концентрацией инфраструктурной и бизнес-логики.
8. Критический рефакторинг по результатам Maintainability Index не требуется.
9. Файлы с минимальными значениями следует рассматривать как кандидатов для дополнительного анализа, а не автоматически переписывать ради улучшения метрики.

Общую поддерживаемость проекта по результатам анализа можно оценить как **высокую**.

---

## Приложение A. Полный результат Content Service

```text
services/content_service/tests/__init__.py - A (100.00)
services/content_service/tests/functional/conftest.py - A (100.00)
services/content_service/tests/functional/__init__.py - A (100.00)
services/content_service/tests/functional/settings.py - A (58.51)
services/content_service/tests/functional/test_data/responses.py - A (100.00)
services/content_service/tests/functional/test_data/persons.py - A (64.07)
services/content_service/tests/functional/test_data/__init__.py - A (100.00)
services/content_service/tests/functional/test_data/films.py - A (43.29)
services/content_service/tests/functional/test_data/genres.py - A (66.90)
services/content_service/tests/functional/utils/__init__.py - A (100.00)
services/content_service/tests/functional/utils/helpers.py - A (47.47)
services/content_service/tests/functional/fixtures/persons.py - A (100.00)
services/content_service/tests/functional/fixtures/__init__.py - A (100.00)
services/content_service/tests/functional/fixtures/common.py - A (100.00)
services/content_service/tests/functional/fixtures/redis.py - A (100.00)
services/content_service/tests/functional/fixtures/http.py - A (100.00)
services/content_service/tests/functional/fixtures/elastic.py - A (100.00)
services/content_service/tests/functional/fixtures/films.py - A (63.22)
services/content_service/tests/functional/fixtures/genres.py - A (100.00)
services/content_service/tests/functional/src/__init__.py - A (100.00)
services/content_service/tests/functional/src/genres/test_genre_detail.py - A (46.58)
services/content_service/tests/functional/src/genres/__init__.py - A (100.00)
services/content_service/tests/functional/src/genres/test_genre_list.py - A (45.42)
services/content_service/tests/functional/src/films/test_film_similar.py - A (26.33)
services/content_service/tests/functional/src/films/__init__.py - A (100.00)
services/content_service/tests/functional/src/films/test_film_list.py - A (38.33)
services/content_service/tests/functional/src/films/test_film_search.py - A (34.47)
services/content_service/tests/functional/src/films/test_film_detail.py - A (41.10)
services/content_service/tests/functional/src/persons/__init__.py - A (100.00)
services/content_service/tests/functional/src/persons/test_person_detail.py - A (46.84)
services/content_service/tests/functional/src/persons/test_person_search.py - A (45.61)
services/content_service/tests/functional/src/persons/test_person_films.py - A (29.07)
services/content_service/src/__init__.py - A (100.00)
services/content_service/src/main.py - A (100.00)
services/content_service/src/core/config.py - A (100.00)
services/content_service/src/core/__init__.py - A (100.00)
services/content_service/src/core/logger.py - A (100.00)
services/content_service/src/cache/__init__.py - A (100.00)
services/content_service/src/cache/redis.py - A (57.52)
services/content_service/src/cache/base.py - A (100.00)
services/content_service/src/repositories/__init__.py - A (100.00)
services/content_service/src/repositories/elastic/film.py - A (100.00)
services/content_service/src/repositories/elastic/person.py - A (100.00)
services/content_service/src/repositories/elastic/__init__.py - A (100.00)
services/content_service/src/repositories/elastic/genre.py - A (100.00)
services/content_service/src/repositories/elastic/bodies/persons.py - A (58.97)
services/content_service/src/repositories/elastic/bodies/__init__.py - A (100.00)
services/content_service/src/repositories/elastic/bodies/films.py - A (61.63)
services/content_service/src/repositories/elastic/bodies/genres.py - A (64.28)
services/content_service/src/repositories/elastic/mappers/__init__.py - A (100.00)
services/content_service/src/repositories/elastic/mappers/films.py - A (100.00)
services/content_service/src/repositories/interfaces/film.py - A (100.00)
services/content_service/src/repositories/interfaces/person.py - A (100.00)
services/content_service/src/repositories/interfaces/__init__.py - A (100.00)
services/content_service/src/repositories/interfaces/genre.py - A (100.00)
services/content_service/src/models/film.py - A (69.39)
services/content_service/src/models/person.py - A (100.00)
services/content_service/src/models/__init__.py - A (100.00)
services/content_service/src/models/genre.py - A (94.30)
services/content_service/src/db/__init__.py - A (100.00)
services/content_service/src/db/redis.py - A (60.77)
services/content_service/src/db/elastic.py - A (61.98)
services/content_service/src/api/__init__.py - A (100.00)
services/content_service/src/api/dependencies.py - A (100.00)
services/content_service/src/api/v1/__init__.py - A (100.00)
services/content_service/src/api/v1/router.py - A (100.00)
services/content_service/src/api/v1/endpoints/persons.py - A (73.31)
services/content_service/src/api/v1/endpoints/films.py - A (74.19)
services/content_service/src/api/v1/endpoints/genres.py - A (80.95)
services/content_service/src/api/v1/schemas/persons.py - A (100.00)
services/content_service/src/api/v1/schemas/films.py - A (55.89)
services/content_service/src/api/v1/schemas/genres.py - A (100.00)
services/content_service/src/api/v1/mappers/persons.py - A (100.00)
services/content_service/src/api/v1/mappers/films.py - A (100.00)
services/content_service/src/api/v1/mappers/genres.py - A (100.00)
services/content_service/src/services/film.py - A (60.57)
services/content_service/src/services/person.py - A (62.51)
services/content_service/src/services/__init__.py - A (100.00)
services/content_service/src/services/genre.py - A (68.47)
services/content_service/src/services/cache_keys/persons.py - A (100.00)
services/content_service/src/services/cache_keys/__init__.py - A (100.00)
services/content_service/src/services/cache_keys/films.py - A (88.41)
services/content_service/src/services/cache_keys/genres.py - A (100.00)
```

---

## Приложение B. Полный результат Content ETL

```text
services/content_etl/postgres_to_es/bootstrap.py - A (55.87)
services/content_etl/postgres_to_es/service.py - A (56.74)
services/content_etl/postgres_to_es/config.py - A (61.16)
services/content_etl/postgres_to_es/__init__.py - A (100.00)
services/content_etl/postgres_to_es/backoff.py - A (53.05)
services/content_etl/postgres_to_es/main.py - A (75.29)
services/content_etl/postgres_to_es/pipelines/persons.py - A (56.39)
services/content_etl/postgres_to_es/pipelines/__init__.py - A (100.00)
services/content_etl/postgres_to_es/pipelines/films.py - A (53.57)
services/content_etl/postgres_to_es/pipelines/base.py - A (55.86)
services/content_etl/postgres_to_es/pipelines/genres.py - A (65.00)
services/content_etl/postgres_to_es/models/person.py - A (100.00)
services/content_etl/postgres_to_es/models/__init__.py - A (100.00)
services/content_etl/postgres_to_es/models/movies.py - A (58.36)
services/content_etl/postgres_to_es/models/postgres_models.py - A (52.29)
services/content_etl/postgres_to_es/models/common.py - A (69.47)
services/content_etl/postgres_to_es/models/genre.py - A (71.58)
services/content_etl/postgres_to_es/state/__init__.py - A (100.00)
services/content_etl/postgres_to_es/state/redis.py - A (55.72)
services/content_etl/postgres_to_es/state/manager.py - A (66.22)
services/content_etl/postgres_to_es/state/base.py - A (100.00)
services/content_etl/postgres_to_es/transforms/persons.py - A (53.02)
services/content_etl/postgres_to_es/transforms/__init__.py - A (100.00)
services/content_etl/postgres_to_es/transforms/movies.py - A (58.35)
services/content_etl/postgres_to_es/transforms/genres.py - A (68.01)
services/content_etl/postgres_to_es/sources/__init__.py - A (100.00)
services/content_etl/postgres_to_es/sources/postgres.py - A (32.72)
services/content_etl/postgres_to_es/loaders/__init__.py - A (100.00)
services/content_etl/postgres_to_es/loaders/elastic.py - A (40.83)
services/content_etl/postgres_to_es/interfaces/__init__.py - A (100.00)
services/content_etl/postgres_to_es/interfaces/retry.py - A (100.00)
services/content_etl/postgres_to_es/interfaces/connection.py - A (100.00)
services/content_etl/postgres_to_es/interfaces/sources.py - A (100.00)
services/content_etl/postgres_to_es/interfaces/loader.py - A (100.00)
```

---

## Приложение C. Полный результат Auth Service

```text
services/auth_service/tests/__init__.py - A (100.00)
services/auth_service/tests/functional/conftest.py - A (100.00)
services/auth_service/tests/functional/__init__.py - A (100.00)
services/auth_service/tests/functional/settings.py - A (100.00)
services/auth_service/tests/functional/test_data/auth.py - A (100.00)
services/auth_service/tests/functional/test_data/responses.py - A (100.00)
services/auth_service/tests/functional/test_data/users.py - A (59.92)
services/auth_service/tests/functional/test_data/roles.py - A (49.17)
services/auth_service/tests/functional/test_data/__init__.py - A (100.00)
services/auth_service/tests/functional/test_data/common.py - A (100.00)
services/auth_service/tests/functional/test_data/permissions.py - A (58.26)
services/auth_service/tests/functional/utils/__init__.py - A (100.00)
services/auth_service/tests/functional/utils/helpers.py - A (61.77)
services/auth_service/tests/functional/fixtures/auth.py - A (35.89)
services/auth_service/tests/functional/fixtures/__init__.py - A (100.00)
services/auth_service/tests/functional/fixtures/common.py - A (100.00)
services/auth_service/tests/functional/fixtures/redis.py - A (100.00)
services/auth_service/tests/functional/fixtures/http.py - A (100.00)
services/auth_service/tests/functional/fixtures/postgres.py - A (100.00)
services/auth_service/tests/functional/src/__init__.py - A (100.00)
services/auth_service/tests/functional/src/auth/test_login.py - A (37.62)
services/auth_service/tests/functional/src/auth/__init__.py - A (100.00)
services/auth_service/tests/functional/src/auth/test_register.py - A (35.26)
services/auth_service/tests/functional/src/auth/test_refresh.py - A (38.48)
services/auth_service/tests/functional/src/auth/test_logout.py - A (38.92)
services/auth_service/tests/functional/src/roles/test_create_role.py - A (36.79)
services/auth_service/tests/functional/src/roles/__init__.py - A (100.00)
services/auth_service/tests/functional/src/roles/test_delete_role.py - A (36.91)
services/auth_service/tests/functional/src/roles/test_get_roles.py - A (31.48)
services/auth_service/tests/functional/src/roles/test_update_role.py - A (25.82)
services/auth_service/tests/functional/src/permissions/test_create_permission.py - A (36.11)
services/auth_service/tests/functional/src/permissions/test_get_permissions.py - A (30.26)
services/auth_service/tests/functional/src/permissions/__init__.py - A (100.00)
services/auth_service/tests/functional/src/permissions/test_check_permission.py - A (42.25)
services/auth_service/tests/functional/src/permissions/test_update_permission.py - A (21.15)
services/auth_service/tests/functional/src/users/test_user_roles.py - A (29.54)
services/auth_service/tests/functional/src/users/__init__.py - A (100.00)
services/auth_service/tests/functional/src/users/test_update_user.py - A (38.22)
services/auth_service/tests/functional/src/users/test_password.py - A (41.44)
services/auth_service/tests/functional/src/users/test_login_history.py - A (30.81)
services/auth_service/tests/functional/src/users/test_get_user.py - A (43.19)
services/auth_service/alembic/env.py - A (72.94)
services/auth_service/alembic/versions/063da50fd6fc_create_auth_tables.py - A (100.00)
services/auth_service/src/__init__.py - A (100.00)
services/auth_service/src/main.py - A (100.00)
services/auth_service/src/core/config.py - A (100.00)
services/auth_service/src/core/security.py - A (100.00)
services/auth_service/src/core/__init__.py - A (100.00)
services/auth_service/src/core/logger.py - A (100.00)
services/auth_service/src/core/jwt.py - A (64.88)
services/auth_service/src/cache/__init__.py - A (100.00)
services/auth_service/src/cache/redis.py - A (52.46)
services/auth_service/src/cache/base.py - A (100.00)
services/auth_service/src/repositories/__init__.py - A (100.00)
services/auth_service/src/repositories/postgres/user.py - A (60.93)
services/auth_service/src/repositories/postgres/permission.py - A (65.18)
services/auth_service/src/repositories/postgres/__init__.py - A (100.00)
services/auth_service/src/repositories/postgres/role.py - A (61.97)
services/auth_service/src/repositories/postgres/refresh_session.py - A (64.76)
services/auth_service/src/repositories/postgres/login_history.py - A (66.84)
services/auth_service/src/repositories/interfaces/user.py - A (100.00)
services/auth_service/src/repositories/interfaces/permission.py - A (100.00)
services/auth_service/src/repositories/interfaces/__init__.py - A (100.00)
services/auth_service/src/repositories/interfaces/role.py - A (100.00)
services/auth_service/src/repositories/interfaces/refresh_session.py - A (100.00)
services/auth_service/src/repositories/interfaces/login_history.py - A (100.00)
services/auth_service/src/models/user.py - A (59.20)
services/auth_service/src/models/permission.py - A (67.09)
services/auth_service/src/models/__init__.py - A (100.00)
services/auth_service/src/models/role.py - A (64.88)
services/auth_service/src/models/refresh_session.py - A (59.04)
services/auth_service/src/models/association.py - A (100.00)
services/auth_service/src/models/entity.py - A (100.00)
services/auth_service/src/models/login_history.py - A (57.37)
services/auth_service/src/db/__init__.py - A (100.00)
services/auth_service/src/db/redis.py - A (60.77)
services/auth_service/src/db/postgres.py - A (58.43)
services/auth_service/src/api/__init__.py - A (100.00)
services/auth_service/src/api/dependencies.py - A (47.40)
services/auth_service/src/api/v1/exception_handlers.py - A (100.00)
services/auth_service/src/api/v1/__init__.py - A (100.00)
services/auth_service/src/api/v1/router.py - A (100.00)
services/auth_service/src/api/v1/endpoints/auth.py - A (100.00)
services/auth_service/src/api/v1/endpoints/users.py - A (100.00)
services/auth_service/src/api/v1/endpoints/roles.py - A (100.00)
services/auth_service/src/api/v1/endpoints/__init__.py - A (100.00)
services/auth_service/src/api/v1/endpoints/permissions.py - A (77.40)
services/auth_service/src/api/v1/schemas/auth.py - A (100.00)
services/auth_service/src/api/v1/schemas/users.py - A (56.45)
services/auth_service/src/api/v1/schemas/roles.py - A (56.54)
services/auth_service/src/api/v1/schemas/__init__.py - A (100.00)
services/auth_service/src/api/v1/schemas/entity.py - A (100.00)
services/auth_service/src/api/v1/schemas/permissions.py - A (60.56)
services/auth_service/src/api/v1/schemas/login_history.py - A (66.13)
services/auth_service/src/api/v1/mappers/auth.py - A (100.00)
services/auth_service/src/api/v1/mappers/__init__.py - A (100.00)
services/auth_service/src/commands/create_superuser.py - A (51.31)
services/auth_service/src/commands/__init__.py - A (100.00)
services/auth_service/src/services/auth.py - A (33.44)
services/auth_service/src/services/user.py - A (35.46)
services/auth_service/src/services/token.py - A (57.71)
services/auth_service/src/services/permission.py - A (38.82)
services/auth_service/src/services/__init__.py - A (100.00)
services/auth_service/src/services/role.py - A (34.14)
services/auth_service/src/services/exceptions.py - A (100.00)
services/auth_service/src/services/cache_keys/users.py - A (100.00)
services/auth_service/src/services/cache_keys/roles.py - A (100.00)
services/auth_service/src/services/cache_keys/__init__.py - A (100.00)
services/auth_service/src/services/cache_keys/permissions.py - A (100.00)
```