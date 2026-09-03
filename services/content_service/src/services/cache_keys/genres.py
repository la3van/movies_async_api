"""Функции создания ключей для кеша жанров."""


def get_genre_cache_key(genre_id: str) -> str:
    """Формирует ключ кеша для одного жанра."""
    return f"genre:{genre_id}"


def get_genres_cache_key(
    query: str | None,
    sort: str | None,
    page_number: int,
    page_size: int,
) -> str:
    """Формирует ключ кеша для списка жанров.

    Ключ учитывает поисковый запрос, сортировку и параметры пагинации.
    """
    normalized_query = query.strip().lower() if query else "all"
    normalized_sort = sort if sort else "none"
    return (
        f"genres:query={normalized_query}:sort={normalized_sort}:"
        f"page_number={page_number}:page_size={page_size}"
    )
