# Ревью поддерживаемости проекта `movies_async_api`

## 1. Цель ревью

Цель ревью — объективно оценить поддерживаемость Python-кода проекта с помощью автоматической метрики **Maintainability Index**.

Для анализа использован инструмент **Radon**. Проект проверен по трём отдельным частям:

1. сервис Async API;
2. ETL-сервис;
3. сервис функциональных тестов.

Раздельный анализ позволяет не смешивать продуктовый код, ETL-логику и тестовую инфраструктуру, поскольку эти части проекта имеют разное назначение и структуру.

---

## 2. Методика анализа

Анализ выполнялся из корневой директории проекта следующими командами:

```bash
radon mi async_api/src -s
radon mi etl/postgres_to_es -s
radon mi tests/functional -s
```

Флаг `-s` используется для отображения не только буквенной категории, но и точного числового значения Maintainability Index.

При интерпретации результатов использовались следующие категории:

| Значение MI | Категория | Интерпретация |
|---:|:---:|---|
| 20–100 | A | высокая поддерживаемость |
| 10–19 | B | средняя поддерживаемость |
| 0–9 | C | низкая поддерживаемость |

Поскольку категория `A` охватывает большой диапазон значений, при анализе учитывалась не только буквенная оценка, но и числовое значение индекса.

Важно учитывать, что Maintainability Index является относительной автоматической метрикой. Низкое по сравнению с другими файлами значение не означает наличие ошибки, но указывает на файл, который стоит изучить дополнительно.

---

# 3. Результаты анализа Async API

Команда:

```bash
radon mi async_api/src -s
```

Полученный результат:

```text
async_api/src/main.py - A (100.00)
async_api/src/core/config.py - A (100.00)
async_api/src/core/__init__.py - A (100.00)
async_api/src/core/logger.py - A (100.00)
async_api/src/cache/__init__.py - A (100.00)
async_api/src/cache/redis.py - A (57.52)
async_api/src/cache/base.py - A (100.00)
async_api/src/repositories/__init__.py - A (100.00)
async_api/src/repositories/elastic/film.py - A (100.00)
async_api/src/repositories/elastic/person.py - A (100.00)
async_api/src/repositories/elastic/__init__.py - A (100.00)
async_api/src/repositories/elastic/genre.py - A (100.00)
async_api/src/repositories/elastic/bodies/persons.py - A (58.97)
async_api/src/repositories/elastic/bodies/__init__.py - A (100.00)
async_api/src/repositories/elastic/bodies/films.py - A (61.63)
async_api/src/repositories/elastic/bodies/genres.py - A (64.28)
async_api/src/repositories/elastic/mappers/__init__.py - A (100.00)
async_api/src/repositories/elastic/mappers/films.py - A (100.00)
async_api/src/repositories/interfaces/film.py - A (100.00)
async_api/src/repositories/interfaces/person.py - A (100.00)
async_api/src/repositories/interfaces/__init__.py - A (100.00)
async_api/src/repositories/interfaces/genre.py - A (100.00)
async_api/src/models/film.py - A (69.39)
async_api/src/models/person.py - A (100.00)
async_api/src/models/__init__.py - A (100.00)
async_api/src/models/genre.py - A (94.30)
async_api/src/db/__init__.py - A (100.00)
async_api/src/db/redis.py - A (60.77)
async_api/src/db/elastic.py - A (61.98)
async_api/src/api/__init__.py - A (100.00)
async_api/src/api/dependencies.py - A (100.00)
async_api/src/api/v1/__init__.py - A (100.00)
async_api/src/api/v1/router.py - A (100.00)
async_api/src/api/v1/endpoints/persons.py - A (73.31)
async_api/src/api/v1/endpoints/films.py - A (78.37)
async_api/src/api/v1/endpoints/genres.py - A (80.95)
async_api/src/api/v1/schemas/persons.py - A (100.00)
async_api/src/api/v1/schemas/films.py - A (55.89)
async_api/src/api/v1/schemas/genres.py - A (100.00)
async_api/src/api/v1/mappers/persons.py - A (100.00)
async_api/src/api/v1/mappers/films.py - A (100.00)
async_api/src/api/v1/mappers/genres.py - A (100.00)
async_api/src/services/film.py - A (60.57)
async_api/src/services/person.py - A (62.51)
async_api/src/services/__init__.py - A (100.00)
async_api/src/services/genre.py - A (68.47)
async_api/src/services/cache_keys/persons.py - A (100.00)
async_api/src/services/cache_keys/__init__.py - A (100.00)
async_api/src/services/cache_keys/films.py - A (88.41)
async_api/src/services/cache_keys/genres.py - A (100.00)
```

## 3.1. Анализ результата

Все файлы Async API получили категорию `A`. Это означает, что по метрике Maintainability Index код сервиса имеет высокую поддерживаемость.

Минимальные значения обнаружены в следующих файлах:

| Файл | MI |
|---|---:|
| `async_api/src/api/v1/schemas/films.py` | 55.89 |
| `async_api/src/cache/redis.py` | 57.52 |
| `async_api/src/repositories/elastic/bodies/persons.py` | 58.97 |
| `async_api/src/services/film.py` | 60.57 |
| `async_api/src/db/redis.py` | 60.77 |
| `async_api/src/repositories/elastic/bodies/films.py` | 61.63 |
| `async_api/src/db/elastic.py` | 61.98 |
| `async_api/src/services/person.py` | 62.51 |

Даже минимальное значение `55.89` значительно превышает нижнюю границу категории `A`. Поэтому критических проблем с поддерживаемостью Async API по результатам анализа не выявлено.

Файлы со значением `100.00` в основном являются небольшими, декларативными или содержат ограниченное количество исполняемой логики. Поэтому значение `100.00` не следует воспринимать как абсолютное доказательство идеального качества кода, а более низкие значения полноценных сервисных модулей — как наличие дефекта.

## 3.2. Возможные улучшения

Обязательный рефакторинг Async API по результатам Maintainability Index не требуется.

В дальнейшем можно дополнительно обратить внимание на:

- `api/v1/schemas/films.py`;
- `cache/redis.py`;
- `services/film.py`;
- тела Elasticsearch-запросов в `repositories/elastic/bodies`.

Эти файлы имеют самые низкие показатели внутри сервиса, однако все они остаются в категории высокой поддерживаемости.

---

# 4. Результаты анализа ETL

Команда:

```bash
radon mi etl/postgres_to_es -s
```

Полученный результат:

```text
etl/postgres_to_es/bootstrap.py - A (55.87)
etl/postgres_to_es/service.py - A (56.74)
etl/postgres_to_es/config.py - A (68.53)
etl/postgres_to_es/__init__.py - A (100.00)
etl/postgres_to_es/backoff.py - A (53.05)
etl/postgres_to_es/main.py - A (75.29)
etl/postgres_to_es/pipelines/persons.py - A (56.39)
etl/postgres_to_es/pipelines/__init__.py - A (100.00)
etl/postgres_to_es/pipelines/films.py - A (53.57)
etl/postgres_to_es/pipelines/base.py - A (55.86)
etl/postgres_to_es/pipelines/genres.py - A (65.00)
etl/postgres_to_es/models/person.py - A (100.00)
etl/postgres_to_es/models/__init__.py - A (100.00)
etl/postgres_to_es/models/movies.py - A (58.36)
etl/postgres_to_es/models/postgres_models.py - A (52.29)
etl/postgres_to_es/models/common.py - A (69.47)
etl/postgres_to_es/models/genre.py - A (71.58)
etl/postgres_to_es/state/__init__.py - A (100.00)
etl/postgres_to_es/state/redis.py - A (55.72)
etl/postgres_to_es/state/manager.py - A (66.22)
etl/postgres_to_es/state/base.py - A (100.00)
etl/postgres_to_es/transforms/persons.py - A (53.02)
etl/postgres_to_es/transforms/__init__.py - A (100.00)
etl/postgres_to_es/transforms/movies.py - A (58.35)
etl/postgres_to_es/transforms/genres.py - A (68.01)
etl/postgres_to_es/sources/__init__.py - A (100.00)
etl/postgres_to_es/sources/postgres.py - A (32.72)
etl/postgres_to_es/loaders/__init__.py - A (100.00)
etl/postgres_to_es/loaders/elastic.py - A (40.83)
etl/postgres_to_es/interfaces/__init__.py - A (100.00)
etl/postgres_to_es/interfaces/retry.py - A (100.00)
etl/postgres_to_es/interfaces/connection.py - A (100.00)
etl/postgres_to_es/interfaces/sources.py - A (100.00)
etl/postgres_to_es/interfaces/loader.py - A (100.00)
```

## 4.1. Анализ результата

Все файлы ETL-сервиса получили категорию `A`.

Минимальные значения обнаружены в следующих файлах:

| Файл | MI |
|---|---:|
| `etl/postgres_to_es/sources/postgres.py` | 32.72 |
| `etl/postgres_to_es/loaders/elastic.py` | 40.83 |
| `etl/postgres_to_es/models/postgres_models.py` | 52.29 |
| `etl/postgres_to_es/transforms/persons.py` | 53.02 |
| `etl/postgres_to_es/backoff.py` | 53.05 |
| `etl/postgres_to_es/pipelines/films.py` | 53.57 |
| `etl/postgres_to_es/state/redis.py` | 55.72 |
| `etl/postgres_to_es/pipelines/base.py` | 55.86 |
| `etl/postgres_to_es/bootstrap.py` | 55.87 |
| `etl/postgres_to_es/pipelines/persons.py` | 56.39 |
| `etl/postgres_to_es/service.py` | 56.74 |

Наиболее низкий показатель ETL-сервиса имеет файл:

```text
etl/postgres_to_es/sources/postgres.py — A (32.72)
```

Второй по величине минимальный показатель:

```text
etl/postgres_to_es/loaders/elastic.py — A (40.83)
```

Оба файла отвечают за инфраструктурную работу с внешними хранилищами данных. Такие модули обычно содержат обработку соединений, пакетную работу с данными, циклы, обработку ошибок и повторные попытки. Это может снижать числовое значение Maintainability Index по сравнению с небольшими интерфейсами и моделями.

При этом оба файла остаются в категории `A`, поэтому результат не указывает на критическую проблему.

## 4.2. Возможные улучшения

Наиболее целесообразно дополнительно проверить:

- размер `sources/postgres.py`;
- сложность отдельных методов источника данных;
- размер `loaders/elastic.py`;
- разделение ответственности между загрузкой данных, формированием bulk-запросов и обработкой ошибок.

Если в этих файлах одновременно выполняется несколько независимых задач, возможным улучшением может быть выделение отдельных вспомогательных компонентов или функций.

Однако выполнять декомпозицию только на основании текущего MI не требуется. Перед рефакторингом следует дополнительно проверить цикломатическую сложность методов и количество строк кода.

---

# 5. Результаты анализа функциональных тестов

Команда:

```bash
radon mi tests/functional -s
```

Полученный результат:

```text
tests/functional/conftest.py - A (100.00)
tests/functional/__init__.py - A (100.00)
tests/functional/settings.py - A (48.01)
tests/functional/testdata/responses.py - A (100.00)
tests/functional/testdata/documents.py - A (42.31)
tests/functional/testdata/__init__.py - A (100.00)
tests/functional/utils/__init__.py - A (100.00)
tests/functional/utils/wait_for_es.py - A (60.89)
tests/functional/utils/wait_for_redis.py - A (61.76)
tests/functional/utils/helpers.py - A (47.47)
tests/functional/src/test_search.py - A (33.72)
tests/functional/src/__init__.py - A (100.00)
tests/functional/src/genres/test_genres.py - A (49.01)
tests/functional/src/films/test_films.py - A (27.17)
tests/functional/src/persons/test_persons.py - A (36.56)
```

## 5.1. Анализ результата

Все файлы сервиса функциональных тестов получили категорию `A`.

Минимальные значения:

| Файл | MI |
|---|---:|
| `tests/functional/src/films/test_films.py` | 27.17 |
| `tests/functional/src/test_search.py` | 33.72 |
| `tests/functional/src/persons/test_persons.py` | 36.56 |
| `tests/functional/testdata/documents.py` | 42.31 |
| `tests/functional/utils/helpers.py` | 47.47 |
| `tests/functional/settings.py` | 48.01 |
| `tests/functional/src/genres/test_genres.py` | 49.01 |

Самый низкий Maintainability Index во всём проекте обнаружен в файле:

```text
tests/functional/src/films/test_films.py — A (27.17)
```

Несмотря на сравнительно низкое значение, файл всё ещё относится к категории высокой поддерживаемости.

Тестовые файлы могут получать более низкий индекс из-за:

- большого количества тестовых сценариев;
- повторяющейся структуры проверок;
- подготовки входных данных;
- большого количества `assert`;
- параметризации;
- наличия негативных и граничных сценариев в одном модуле.

Файл `testdata/documents.py` содержит тестовые данные, поэтому его более низкий показатель сам по себе не является достаточным основанием для декомпозиции. Разделение такого файла имеет смысл только в том случае, если навигация по данным действительно затруднена.

## 5.2. Возможные улучшения

Для тестов можно рассмотреть следующие улучшения:

- параметризовать однотипные тестовые сценарии;
- вынести повторяющуюся подготовку данных во вспомогательные функции или фикстуры;
- выделить повторяющиеся проверки ответов;
- разделить слишком крупные тестовые модули по группам сценариев;
- не смешивать тестовые данные с логикой выполнения тестов.

В первую очередь дополнительного ручного анализа заслуживают:

- `tests/functional/src/films/test_films.py`;
- `tests/functional/src/test_search.py`;
- `tests/functional/src/persons/test_persons.py`.

При этом по текущим результатам обязательный рефакторинг тестов не требуется.

---

# 6. Сравнение частей проекта

| Часть проекта | Минимальный MI | Файл с минимальным MI | Итоговая категория |
|---|---:|---|:---:|
| Async API | 55.89 | `async_api/src/api/v1/schemas/films.py` | A |
| ETL | 32.72 | `etl/postgres_to_es/sources/postgres.py` | A |
| Функциональные тесты | 27.17 | `tests/functional/src/films/test_films.py` | A |

Из трёх частей проекта самые высокие минимальные показатели имеет Async API.

Более низкие значения ETL объяснимы большей концентрацией инфраструктурной логики, связанной с извлечением, преобразованием и загрузкой данных.

Самые низкие показатели находятся в функциональных тестах. Это связано с тем, что отдельные тестовые модули содержат большое количество сценариев и проверок. Несмотря на это, все файлы тестового сервиса также получили категорию `A`.

---

# 7. Общие выводы

По результатам анализа все проверенные Python-файлы проекта получили категорию `A`.

Значений категорий `B` и `C` не обнаружено. Следовательно, Radon не выявил файлов с низкой или критически низкой поддерживаемостью.

Основные результаты:

1. Async API имеет высокие показатели поддерживаемости. Минимальный MI равен `55.89`.
2. ETL-сервис также полностью находится в категории `A`. Наиболее низкий показатель равен `32.72` и относится к источнику данных PostgreSQL.
3. Все файлы функциональных тестов получили категорию `A`. Минимальный показатель равен `27.17`.
4. Наиболее низкие значения сосредоточены в файлах, содержащих основную инфраструктурную или тестовую логику.
5. Критический рефакторинг по результатам Maintainability Index не требуется.
6. Файлы с минимальными значениями целесообразно использовать как кандидатов для дополнительного анализа, но не следует изменять их только ради увеличения метрики.

Общую поддерживаемость проекта по результатам анализа можно оценить как **высокую**.

---

# 8. Рекомендации

Для более подробного анализа файлов с минимальными значениями можно дополнительно выполнить:

```bash
radon cc async_api/src -s -a
radon cc etl/postgres_to_es -s -a
radon cc tests/functional -s -a
```

Эти команды покажут цикломатическую сложность функций, методов и классов.

Дополнительно можно проверить размер отдельных файлов:

```bash
radon raw \
  async_api/src/api/v1/schemas/films.py \
  async_api/src/cache/redis.py \
  async_api/src/services/film.py \
  etl/postgres_to_es/sources/postgres.py \
  etl/postgres_to_es/loaders/elastic.py \
  tests/functional/src/films/test_films.py \
  tests/functional/src/test_search.py \
  tests/functional/src/persons/test_persons.py \
  -s
```

Дальнейший рефакторинг имеет смысл выполнять только в том случае, если дополнительный анализ покажет:

- функции с высокой цикломатической сложностью;
- чрезмерно большие методы;
- повторяющуюся логику;
- смешение нескольких обязанностей в одном модуле;
- затруднённую навигацию по тестовым сценариям.

На основании текущего анализа Maintainability Index существенных проблем с поддерживаемостью проекта не обнаружено.
