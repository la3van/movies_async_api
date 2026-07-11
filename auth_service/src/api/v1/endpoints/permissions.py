"""Эндпоинты прав доступа."""
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from api.dependencies import (
    get_current_active_user,
    get_permission_service,
    require_superuser,
)
from api.v1.schemas.permissions import (
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
)
from api.v1.schemas.users import UserResponse
from services.permission import PermissionService


router = APIRouter(prefix='/permissions', tags=['permissions'])


@router.post(
    '/check',
    response_model=PermissionCheckResponse,
    summary='Проверка права доступа',
    description=(
        'Проверяет, есть ли у текущего пользователя '
        'указанное право доступа.'
    ),
    response_description='Результат проверки права доступа',
)
async def check_permission(
    permission_data: PermissionCheckRequest,
    current_user: UserResponse = (
        Depends(get_current_active_user)  # noqa: B008
    ),
) -> PermissionCheckResponse:
    """Проверяет наличие права у текущего пользователя."""

    has_permission = current_user.is_superuser or any(
        permission.code == permission_data.permission_code
        for role in current_user.roles
        for permission in role.permissions
    )

    return PermissionCheckResponse(has_permission=has_permission)


@router.get(
    '/',
    response_model=list[PermissionResponse],
    summary='Список прав доступа',
    description='Возвращает список прав доступа с пагинацией.',
    response_description='Список прав доступа',
)
async def get_permissions(
    limit: int = Query(  # noqa: B008
        100,
        ge=1,
        le=500,
        description='Максимальное количество прав в ответе',
        examples=[100],
    ),
    offset: int = Query(  # noqa: B008
        0,
        ge=0,
        description='Смещение от начала списка',
        examples=[0],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    permission_service: PermissionService = (
        Depends(get_permission_service)  # noqa: B008
    ),
) -> list[PermissionResponse]:
    """Возвращает список прав доступа."""
    return await permission_service.get_all(limit=limit, offset=offset)


@router.get(
    '/{permission_id}',
    response_model=PermissionResponse,
    summary='Право доступа по идентификатору',
    description='Возвращает одно право доступа по его UUID.',
    response_description='Право доступа',
)
async def get_permission(
    permission_id: UUID = Path(  # noqa: B008
        ...,
        description='UUID права доступа',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    permission_service: PermissionService = (
        Depends(get_permission_service)  # noqa: B008
    ),
) -> PermissionResponse:
    """Возвращает право доступа по идентификатору."""
    return await permission_service.get_by_id(permission_id)


@router.post(
    '/',
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Создание права доступа',
    description='Создаёт новое право доступа в системе.',
    response_description='Созданное право доступа',
)
async def create_permission(
    permission_data: PermissionCreate,
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    permission_service: PermissionService = (
        Depends(get_permission_service)  # noqa: B008
    ),
) -> PermissionResponse:
    """Создаёт новое право доступа."""
    return await permission_service.create(permission_data)


@router.patch(
    '/{permission_id}',
    response_model=PermissionResponse,
    summary='Обновление права доступа',
    description='Обновляет код и описание права доступа.',
    response_description='Обновлённое право доступа',
)
async def update_permission(
    permission_id: UUID = Path(  # noqa: B008
        ...,
        description='UUID права доступа',
        examples=['6f822a92-7b51-4753-8d00-ecfedf98a937'],
    ),
    permission_data: PermissionUpdate = ...,
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    permission_service: PermissionService = (
        Depends(get_permission_service)  # noqa: B008
    ),
) -> PermissionResponse:
    """Обновляет право доступа."""
    return await permission_service.update(
        permission_id=permission_id,
        permission_data=permission_data,
    )
