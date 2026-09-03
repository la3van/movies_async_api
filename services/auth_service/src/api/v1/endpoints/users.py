"""Эндпоинты пользователей."""

from datetime import datetime
from uuid import UUID

from api.dependencies import (
    get_current_active_user,
    get_user_service,
    require_superuser,
)
from api.v1.schemas.login_history import LoginHistoryResponse
from api.v1.schemas.users import (
    UserPasswordUpdate,
    UserResponse,
    UserUpdate,
)
from fastapi import APIRouter, Depends, Path, Query, status
from services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Текущий пользователь",
    description=(
        "Возвращает данные текущего аутентифицированного пользователя."
    ),
    response_description="Профиль текущего пользователя",
)
async def get_me(
    current_user: UserResponse = (
        Depends(get_current_active_user)  # noqa: B008
    ),
) -> UserResponse:
    """Возвращает текущего пользователя."""

    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Обновление профиля",
    description=(
        "Обновляет логин, email, имя или фамилию "
        "текущего аутентифицированного пользователя."
    ),
    response_description="Обновлённый профиль пользователя",
)
async def update_me(
    user_data: UserUpdate,
    current_user: UserResponse = (
        Depends(get_current_active_user)  # noqa: B008
    ),
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserResponse:
    """Обновляет профиль текущего пользователя."""

    return await user_service.update_profile(
        user_id=current_user.id,
        user_data=user_data,
    )


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Смена пароля",
    description=(
        "Меняет пароль текущего пользователя. "
        "Проверяет старый пароль перед установкой нового."
    ),
    response_description="Пароль пользователя успешно изменён",
)
async def change_my_password(
    password_data: UserPasswordUpdate,
    current_user: UserResponse = (
        Depends(get_current_active_user)  # noqa: B008
    ),
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> None:
    """Меняет пароль текущего пользователя."""

    await user_service.change_password(
        user_id=current_user.id,
        password_data=password_data,
    )


@router.get(
    "/me/login-history",
    response_model=list[LoginHistoryResponse],
    summary="История входов",
    description=(
        "Возвращает историю входов текущего пользователя с пагинацией."
    ),
    response_description="Список записей истории входов пользователя",
)
async def get_my_login_history(
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Максимальное количество записей в ответе",
        examples=[50],
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Смещение от начала списка",
        examples=[0],
    ),
    created_from: datetime | None = Query(  # noqa: B008
        description="Нижняя граница времени входа включительно.",
        examples=["2026-07-01T00:00:00Z"],
    ),
    created_to: datetime | None = Query(  # noqa: B008
        description="Верхняя граница времени входа не включительно.",
        examples=["2026-08-01T00:00:00Z"],
    ),
    current_user: UserResponse = (
        Depends(get_current_active_user)  # noqa: B008
    ),
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> list[LoginHistoryResponse]:
    """Возвращает историю входов текущего пользователя."""

    return await user_service.get_login_history(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
        created_from=created_from,
        created_to=created_to,
    )


@router.post(
    "/{user_id}/roles/{role_id}",
    response_model=UserResponse,
    summary="Назначение роли пользователю",
    description=(
        "Назначает пользователю указанную роль. "
        "Доступно только суперпользователю."
    ),
    response_description="Пользователь с обновлённым набором ролей",
)
async def assign_role_to_user(
    user_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID пользователя",
        examples=["6f822a92-7b51-4753-8d00-ecfedf98a937"],
    ),
    role_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID назначаемой роли",
        examples=["7d822a92-7b51-4753-8d00-ecfedf98a938"],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserResponse:
    """Назначает роль пользователю."""

    return await user_service.assign_role(
        user_id=user_id,
        role_id=role_id,
    )


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserResponse,
    summary="Удаление роли у пользователя",
    description=(
        "Удаляет у пользователя указанную роль. "
        "Доступно только суперпользователю."
    ),
    response_description="Пользователь с обновлённым набором ролей",
)
async def remove_role_from_user(
    user_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID пользователя",
        examples=["6f822a92-7b51-4753-8d00-ecfedf98a937"],
    ),
    role_id: UUID = Path(  # noqa: B008
        ...,
        description="UUID удаляемой роли",
        examples=["7d822a92-7b51-4753-8d00-ecfedf98a938"],
    ),
    _current_user: UserResponse = Depends(require_superuser),  # noqa: B008
    user_service: UserService = Depends(get_user_service),  # noqa: B008
) -> UserResponse:
    """Удаляет роль у пользователя."""

    return await user_service.remove_role(
        user_id=user_id,
        role_id=role_id,
    )
