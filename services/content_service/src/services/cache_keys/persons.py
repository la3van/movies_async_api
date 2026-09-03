"""Функции создания ключей для кеша персон."""


def get_person_cache_key(person_id: str) -> str:
    """Формирует ключ кеша для одной персоны."""
    return f"person:{person_id}"


def get_persons_cache_key(
    query: str | None,
    sort: str | None,
    page_number: int,
    page_size: int,
) -> str:
    """Формирует ключ кеша для списка персон.

    Ключ учитывает поисковый запрос, сортировку и параметры пагинации.
    """
    normalized_query = query.strip().lower() if query else "all"
    normalized_sort = sort if sort else "none"
    return (
        f"persons:query={normalized_query}:sort={normalized_sort}:"
        f"page_number={page_number}:page_size={page_size}"
    )


def get_person_films_cache_key(
    person_id: str,
    page_number: int,
    page_size: int,
) -> str:
    """Формирует ключ кеша для списка фильмов персоны.

    Ключ учитывает id персоны и параметры пагинации."""
    return (
        f"person:films:person_id={person_id}:page_number={page_number}:"
        f"page_size={page_size}"
    )
