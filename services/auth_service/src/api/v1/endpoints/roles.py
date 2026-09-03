"""Эндпоинты ролей."""

from typing import Annotated
from uuid import UUID

from api.dependencies import get_role_service, require_superuser
from api.v1.schemas.roles import RoleCreate, RoleResponse, RoleUpdate
from api.v1.schemas.users import UserResponse
from fastapi import APIRouter, Depends, Path, Query, status
from services.role import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get(
    "/",
    response_model=list[RoleResponse],
    summary="Список ролей",
    description="Возвращает список ролей с пагинацией.",
    response_description="Список ролей",
)
async def get_roles(
    limit: int = Query(
        100,
        ge=1,
        le=500,
        description="Максимальное количество ролей в ответе",
        examples=[100],
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Смещение от начала списка",
        examples=[0],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    role_service: RoleService = Depends(get_role_service),  # noqa: B008
) -> list[RoleResponse]:
    """Возвращает список ролей."""
    return await role_service.get_all(limit=limit, offset=offset)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Роль по идентификатору",
    description="Возвращает одну роль по её UUID.",
    response_description="Роль с её правами доступа",
)
async def get_role(
    role_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID роли",
        examples=["6f822a92-7b51-4753-8d00-ecfedf98a937"],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    role_service: RoleService = Depends(get_role_service),  # noqa: B008
) -> RoleResponse:
    """Возвращает роль по идентификатору."""
    return await role_service.get_by_id(role_id)


@router.post(
    "/",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание роли",
    description="Создаёт новую роль в системе.",
    response_description="Созданная роль",
)
async def create_role(
    role_data: RoleCreate,
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    role_service: RoleService = Depends(get_role_service),  # noqa: B008
) -> RoleResponse:
    """Создаёт новую роль."""
    return await role_service.create(role_data)


@router.patch(
    "/{role_id}",
    response_model=RoleResponse,
    summary="Обновление роли",
    description="Обновляет имя, описание и набор прав роли.",
    response_description="Обновлённая роль",
)
async def update_role(
    role_id: Annotated[
        UUID,
        Path(
            ...,
            description="UUID роли",
            examples=["6f822a92-7b51-4753-8d00-ecfedf98a937"],
        ),
    ],
    role_data: RoleUpdate,
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    role_service: RoleService = Depends(get_role_service),  # noqa: B008
) -> RoleResponse:
    """Обновляет роль."""
    return await role_service.update(role_id=role_id, role_data=role_data)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление роли",
    description="Удаляет роль из системы.",
    response_description="Роль успешно удалена",
)
async def delete_role(
    role_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID роли",
        examples=["6f822a92-7b51-4753-8d00-ecfedf98a937"],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    role_service: RoleService = Depends(get_role_service),  # noqa: B008
) -> None:
    """Удаляет роль."""
    await role_service.delete(role_id)
