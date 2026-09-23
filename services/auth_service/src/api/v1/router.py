"""Главный роутер API v1."""

from api.v1.endpoints import (
    auth,
    notification_internal,
    oauth,
    permissions,
    roles,
    users,
)
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
api_router.include_router(oauth.router)
api_router.include_router(notification_internal.router)
