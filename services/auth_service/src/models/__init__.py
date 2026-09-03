"""Импорты SQLAlchemy-моделей auth-сервиса."""

from models.association import role_permissions, user_roles
from models.login_history import LoginHistory
from models.permission import Permission
from models.refresh_session import RefreshSession
from models.role import Role
from models.social_account import SocialAccount
from models.user import User

__all__ = (
    "LoginHistory",
    "Permission",
    "RefreshSession",
    "Role",
    "SocialAccount",
    "User",
    "role_permissions",
    "user_roles",
)
