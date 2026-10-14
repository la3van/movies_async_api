"""Dependencies for self-service, staff access, and restricted workers."""

import secrets
from typing import Annotated

from auth.client import CurrentUser
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from services.profile import ProfileService

bearer = HTTPBearer(auto_error=False)


def get_service(request: Request) -> ProfileService:
    return request.app.state.profile_service


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer)
    ],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            401,
            "access_token_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await request.app.state.auth_client.current_user(
        credentials.credentials, request.state.request_id
    )


async def require_reader(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if not user.can("profiles:read"):
        raise HTTPException(403, "permission_denied")
    return user


async def require_notification_worker(
    request: Request, x_service_token: Annotated[str, Header()] = ""
) -> None:
    expected = request.app.state.settings.notification_token.get_secret_value()
    if not expected or not secrets.compare_digest(
        x_service_token.encode(), expected.encode()
    ):
        raise HTTPException(403, "invalid_service_token")
