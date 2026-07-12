"""Главный роутер API v1."""
from fastapi import APIRouter

from api.v1.endpoints import (
    auth,
    users,
    roles,
    permissions,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(permissions.router)
