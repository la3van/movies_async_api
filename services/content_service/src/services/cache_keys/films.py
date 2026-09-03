"""Функции создания ключей для кеша фильмов."""


def get_film_cache_key(film_id: str) -> str:
    """Формирует ключ кеша для одного фильма."""
    return f"film:{film_id}"


def get_sorted_films_cache_key(
    sort: str,
    genre_filter: str | None,
    page_number: int,
    page_size: int,
) -> str:
    """Формирует ключ кеша для списка фильмов с учётом сортировки,
    жанра и пагинации."""
    normalized_genre_filter = (
        genre_filter.strip() if genre_filter is not None else "all"
    )
    return (
        f"films:sort={sort}:genre={normalized_genre_filter}:"
        f"page={page_number}:size={page_size}"
    )


def get_searched_films_cache_key(
    query: str,
    page_number: int,
    page_size: int,
) -> str:
    """Формирует ключ кеша для результата
    полнотекстового поиска фильмов(нормализуем query)."""
    normalized_query = query.strip().lower()
    return (
        f"films:query={normalized_query}:"
        f"page_number={page_number}:page_size={page_size}"
    )


def get_similar_films_cache_key(
    film_id: str,
    page_number: int,
    page_size: int,
) -> str:
    """Формируем ключ кэша для похожих фильмов."""
    return f"films:similar:film={film_id}:page={page_number}:size={page_size}"
