"""PostgreSQL-реализации репозиториев auth-сервиса."""
from repositories.postgres.login_history import PostgresLoginHistoryRepository
from repositories.postgres.permission import PostgresPermissionRepository
from repositories.postgres.refresh_session import (
    PostgresRefreshSessionRepository
)
from repositories.postgres.role import PostgresRoleRepository
from repositories.postgres.user import PostgresUserRepository
from repositories.postgres.social_account import (
    PostgresSocialAccountRepository
)

__all__ = (
    'PostgresLoginHistoryRepository',
    'PostgresPermissionRepository',
    'PostgresRefreshSessionRepository',
    'PostgresRoleRepository',
    'PostgresUserRepository',
    'PostgresSocialAccountRepository',
)
