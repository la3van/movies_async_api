"""Тестовые данные для permissions эндпоинтов."""
PERMISSION_CODE = 'movies:watch_premium'
PERMISSION_DESCRIPTION = 'Разрешает смотреть премиум-фильмы'

SECOND_PERMISSION_CODE = 'movies:watch_fresh'
SECOND_PERMISSION_DESCRIPTION = 'Разрешает смотреть новые фильмы'

UPDATED_PERMISSION_CODE = 'movies:watch_subscription'
UPDATED_PERMISSION_DESCRIPTION = 'Разрешает смотреть фильмы по подписке'

MISSING_PERMISSION_ID = '00000000-0000-0000-0000-000000000001'


def get_permission_create_data(
    *,
    code: str = PERMISSION_CODE,
    description: str | None = PERMISSION_DESCRIPTION,
) -> dict[str, str | None]:
    """Возвращает payload создания permission."""
    return {
        'code': code,
        'description': description,
    }


def get_second_permission_create_data() -> dict[str, str | None]:
    """Возвращает payload создания второго permission."""
    return get_permission_create_data(
        code=SECOND_PERMISSION_CODE,
        description=SECOND_PERMISSION_DESCRIPTION,
    )


def get_permission_update_data(
    *,
    code: str | None = UPDATED_PERMISSION_CODE,
    description: str | None = UPDATED_PERMISSION_DESCRIPTION,
) -> dict[str, str | None]:
    """Возвращает payload обновления permission."""
    return {
        'code': code,
        'description': description,
    }


def get_duplicate_permission_create_data() -> dict[str, str | None]:
    """Возвращает payload создания permission с уже существующим code."""
    return get_permission_create_data(code=PERMISSION_CODE)
