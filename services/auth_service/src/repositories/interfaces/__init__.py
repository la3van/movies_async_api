"""Интерфейс репозиториев auth-сервиса."""
from repositories.interfaces.login_history import LoginHistoryRepository
from repositories.interfaces.permission import PermissionRepository
from repositories.interfaces.refresh_session import RefreshSessionRepository
from repositories.interfaces.role import RoleRepository
from repositories.interfaces.user import UserRepository

__all__ = (
    'LoginHistoryRepository',
    'PermissionRepository',
    'RefreshSessionRepository',
    'RoleRepository',
    'UserRepository',
)
