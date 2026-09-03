# Ревью поддерживаемости проекта `movies_async_api`

## 1. Цель

Отчёт фиксирует актуальный Maintainability Index Python-кода всех сервисов
проекта. Метрика рассчитана Radon после добавления Events Service, Events ETL
и UGC Service и обновления существующих компонентов.

Maintainability Index помогает находить модули с высокой концентрацией
ветвлений и логики. Он является ориентиром для ручного ревью, а не прямым
доказательством хорошего или плохого качества кода.

## 2. Воспроизведение анализа

Из корня репозитория:

```bash
python -m pip install -r requirements-dev.txt
radon mi services -s
```

Для машиночитаемого результата:

```bash
radon mi services -s -j > radon-mi.json
python -m json.tool radon-mi.json >/dev/null
```

Флаг `-s` добавляет точное числовое значение MI, а `-j` формирует JSON.
Команда анализирует продуктовый код, функциональные тесты и миграции внутри
каталога `services`.

Полный результат команды для всех 402 файлов сохранён в
[`RADON_MI_FULL_REPORT.md`](RADON_MI_FULL_REPORT.md).

Шкала Radon:

| MI | Категория | Интерпретация |
| ---: | :---: | --- |
| 20–100 | A | высокая поддерживаемость |
| 10–19 | B | средняя поддерживаемость |
| 0–9 | C | низкая поддерживаемость |

Категория A охватывает широкий диапазон. Поэтому при сравнении модулей нужно
учитывать числовой показатель, назначение файла и сложность решаемой задачи.

## 3. Общий результат

Дата актуализации: **3 сентября 2026 года**.

Проверено **402 Python-файла**:

- 327 файлов продуктового кода;
- 73 файла функциональных тестов;
- 2 файла Alembic Auth Service.

Распределение результатов:

| Категория | Файлов |
| :---: | ---: |
| A | 402 |
| B | 0 |
| C | 0 |

Все проверенные файлы находятся в категории A.

Минимальный MI всего проекта:

```text
services/auth_service/tests/functional/src/permissions/test_update_permission.py
— A (21.15)
```

Минимальный MI продуктового кода:

```text
services/events_service/src/models/events.py — A (29.64)
```

## 4. Результаты по компонентам

Auth и Content разделены на продуктовый код и функциональные тесты, чтобы
тестовые сценарии не искажали оценку самих приложений.

| Компонент | Файлов | Минимум | Среднее | Медиана | Файл с минимальным MI | Категория |
| --- | ---: | ---: | ---: | ---: | --- | :---: |
| Admin Service | 17 | 46.50 | 85.93 | 100.00 | `services/admin_service/admin_auth/backends.py` | A |
| Auth Service | 93 | 32.72 | 76.99 | 74.96 | `services/auth_service/src/services/user.py` | A |
| Auth — функциональные тесты | 41 | 21.15 | 67.30 | 59.92 | `services/auth_service/tests/functional/src/permissions/test_update_permission.py` | A |
| Auth — Alembic | 2 | 53.51 | 63.23 | 63.23 | `services/auth_service/alembic/versions/6604474198ef_create_auth_schema.py` | A |
| Content Service | 61 | 40.40 | 85.29 | 100.00 | `services/content_service/src/core/rate_limit.py` | A |
| Content — функциональные тесты | 32 | 26.33 | 74.96 | 100.00 | `services/content_service/tests/functional/src/films/test_film_similar.py` | A |
| Content ETL | 34 | 32.72 | 75.30 | 68.74 | `services/content_etl/postgres_to_es/sources/postgres.py` | A |
| Events Service | 32 | 29.64 | 83.84 | 100.00 | `services/events_service/src/models/events.py` | A |
| Events ETL | 23 | 32.85 | 77.63 | 100.00 | `services/events_etl/src/services/etl.py` | A |
| UGC Service | 67 | 41.37 | 81.41 | 100.00 | `services/ugc_service/src/integrations/content.py` | A |

Высокая медиана ряда компонентов связана с большим количеством небольших
`__init__.py`, интерфейсов и декларативных моделей с MI 100. Поэтому для
поиска кандидатов на ручное ревью полезнее минимальные значения.

## 5. Продуктовые файлы с минимальным MI

| Файл | MI | Категория |
| --- | ---: | :---: |
| `services/events_service/src/models/events.py` | 29.64 | A |
| `services/content_etl/postgres_to_es/sources/postgres.py` | 32.72 | A |
| `services/auth_service/src/services/user.py` | 32.72 | A |
| `services/events_etl/src/services/etl.py` | 32.85 | A |
| `services/auth_service/src/services/role.py` | 34.04 | A |
| `services/events_etl/src/kafka/consumer.py` | 34.38 | A |
| `services/auth_service/src/services/auth.py` | 35.51 | A |
| `services/events_etl/src/services/mapper.py` | 36.97 | A |
| `services/auth_service/src/oauth/providers/yandex.py` | 37.52 | A |
| `services/events_service/src/kafka/producer.py` | 38.23 | A |
| `services/auth_service/src/oauth/providers/vk.py` | 39.40 | A |
| `services/auth_service/src/services/permission.py` | 39.91 | A |
| `services/content_service/src/core/rate_limit.py` | 40.40 | A |
| `services/content_etl/postgres_to_es/loaders/elastic.py` | 40.73 | A |
| `services/ugc_service/src/integrations/content.py` | 41.37 | A |

Эти значения ожидаемы для модулей, которые содержат сложную валидацию,
координацию внешних систем, повторные попытки, транзакции или насыщенные
бизнес-правила. Ни один из файлов не требует автоматического рефакторинга
только ради увеличения MI.

## 6. Тестовые файлы с минимальным MI

| Файл | MI | Категория |
| --- | ---: | :---: |
| `services/auth_service/tests/functional/src/permissions/test_update_permission.py` | 21.15 | A |
| `services/auth_service/tests/functional/src/roles/test_update_role.py` | 25.82 | A |
| `services/content_service/tests/functional/src/films/test_film_similar.py` | 26.33 | A |
| `services/content_service/tests/functional/src/persons/test_person_films.py` | 29.07 | A |
| `services/auth_service/tests/functional/src/users/test_user_roles.py` | 29.54 | A |
| `services/auth_service/tests/functional/src/permissions/test_get_permissions.py` | 30.26 | A |
| `services/auth_service/tests/functional/src/users/test_login_history.py` | 30.81 | A |
| `services/auth_service/tests/functional/src/roles/test_get_roles.py` | 31.48 | A |
| `services/content_service/tests/functional/src/films/test_film_search.py` | 34.47 | A |
| `services/auth_service/tests/functional/src/auth/test_register.py` | 35.26 | A |

Более низкий MI функциональных тестов объясняется количеством сценариев,
подготовкой данных, параметризацией и множеством проверок. Пока тесты остаются
понятными и разделены по endpoint и операции, их не следует объединять или
сокращать исключительно ради метрики.

## 7. Выводы

1. Все 402 Python-файла получили категорию A.
2. Файлов категорий B и C не обнаружено.
3. Минимальный MI продуктового кода равен 29.64 и относится к модели событий.
4. Минимальный MI тестов равен 21.15 и относится к обновлению permissions.
5. Самый высокий минимальный показатель среди приложений имеет Admin Service
   — 46.50; следом идёт UGC Service — 41.37.
6. Основные кандидаты для наблюдения находятся в Events Service, Content ETL,
   Auth Service и Events ETL, но все они сохраняют высокий класс A.
7. Критический рефакторинг по результатам Maintainability Index не требуется.

При последующих крупных изменениях отчёт следует генерировать повторно той же
командой и сравнивать прежде всего минимальные значения продуктового кода, а
не среднее по каталогу.
