"""Auth owns identity and permissions; Profile never reads Auth's database."""

from uuid import UUID

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field, StrictBool


class Permission(BaseModel):
    code: str


class Role(BaseModel):
    permissions: list[Permission] = Field(default_factory=list)


class CurrentUser(BaseModel):
    id: UUID
    is_active: StrictBool
    is_superuser: StrictBool = False
    roles: list[Role] = Field(default_factory=list)

    def can(self, permission: str) -> bool:
        return self.is_superuser or any(
            p.code == permission
            for role in self.roles
            for p in role.permissions
        )


class AuthClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def current_user(self, token: str, request_id: str) -> CurrentUser:
        try:
            response = await self.client.get(
                "users/me",
                headers={
                    "Authorization": "Bearer " + token,
                    "X-Request-ID": request_id,
                },
            )
        except httpx.RequestError as exc:
            raise HTTPException(503, "auth_unavailable") from exc
        if response.status_code in {401, 404}:
            raise HTTPException(
                401,
                "invalid_access_token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if response.status_code == 403:
            raise HTTPException(403, "user_forbidden")
        if response.status_code != 200:
            raise HTTPException(503, "auth_unavailable")
        try:
            user = CurrentUser.model_validate(response.json())
        except ValueError as exc:
            raise HTTPException(503, "invalid_auth_response") from exc
        if not user.is_active:
            raise HTTPException(403, "user_forbidden")
        return user
