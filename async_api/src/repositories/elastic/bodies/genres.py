"""Создание body запросов для поиска жанров."""


def build_genres_body(
    query: str | None,
    sort: str | None,
    page_number: int,
    page_size: int,
    genre_sort_fields: dict[str, str],
) -> dict:
    search_query: dict = {
        'match_all': {},
    }
    if query:
        search_query = {
            'multi_match': {
                'query': query,
                'fields': [
                    'name^5',
                    'description',
                ],
            },
        }

    body = {
        'query': search_query,
        'from': (page_number - 1) * page_size,
        'size': page_size,
    }

    if sort:
        order = 'desc' if sort.startswith('-') else 'asc'
        sort_field = genre_sort_fields.get(
            sort.lstrip('-'),
            'name.raw',
        )

        body['sort'] = [
            {
                sort_field: {
                    'order': order,
                },
            },
        ]

    return body
