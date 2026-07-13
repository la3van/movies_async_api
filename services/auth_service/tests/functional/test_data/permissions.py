"""Тестовые данные для permissions эндпоинтов."""
from tests.functional.test_data.common import UNSET, UnsetType

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
    code: str | None | UnsetType = UNSET,
    description: str | UnsetType = UNSET,
) -> dict[str, str | None]:
    """Возвращает payload частичного обновления permission."""
    data: dict[str, None] = {}

    if not isinstance(code, UnsetType):
        data['code'] = code
    if not isinstance(description, UnsetType):
        data['description'] = description

    return data


def get_full_permission_update_data() -> dict[str, str | None]:
    """Возвращает payload обновления всех полей permission."""
    return get_permission_update_data(
        code=UPDATED_PERMISSION_CODE,
        description=UPDATED_PERMISSION_DESCRIPTION,
    )


def get_duplicate_permission_create_data() -> dict[str, str | None]:
    """Возвращает payload создания permission с уже существующим code."""
    return get_permission_create_data(code=PERMISSION_CODE)
