"""Проверка полномочий суперпользователя через существующий Auth."""

from uuid import UUID

import httpx
from fastapi import HTTPException, Request
from pydantic import BaseModel, StrictBool, ValidationError


class Principal(BaseModel):
    """Проверенные признаки пользователя из ответа Auth."""

    id: UUID
    is_active: StrictBool
    is_superuser: StrictBool


async def require_superuser(request: Request) -> UUID:
    """Возвращает UUID активного суперпользователя после проверки Auth."""
    token = request.headers.get("Authorization", "")
    if not token.lower().startswith("bearer ") or not token[7:].strip():
        raise HTTPException(
            401,
            "access_token_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        response = await request.app.state.auth.get(
            "users/me",
            headers={"Authorization": token},
        )
    except httpx.RequestError as exc:
        raise HTTPException(503, "auth_service_unavailable") from exc
    if response.status_code in (401, 404):
        raise HTTPException(
            401, "invalid_access_token", headers={"WWW-Authenticate": "Bearer"}
        )
    if response.status_code == 403:
        raise HTTPException(403, "user_forbidden")
    if response.status_code != 200:
        raise HTTPException(503, "auth_service_unavailable")
    try:
        principal = Principal.model_validate(response.json())
    except (ValidationError, ValueError) as exc:
        raise HTTPException(503, "invalid_auth_response") from exc
    if not principal.is_active or not principal.is_superuser:
        raise HTTPException(403, "superuser_required")
    return principal.id
