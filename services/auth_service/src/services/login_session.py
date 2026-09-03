"""Создание успешной пользовательской login-сессии."""

from models.user import User
from services.token import TokenPair, TokenService
from unit_of_work.base import AbstractUnitOfWork


async def create_login_session(
    *,
    uow: AbstractUnitOfWork,
    token_service: TokenService,
    user: User,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    """Создаёт токены, refresh-сессию и запись истории входа."""

    token_pair, refresh_token_data = token_service.create_token_pair(user)

    await uow.refresh_sessions.create(
        session_id=refresh_token_data.session_id,
        user_id=user.id,
        token_hash=refresh_token_data.token_hash,
        expires_at=refresh_token_data.expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    await uow.login_history.create(
        user_id=user.id,
        login=user.login,
        is_successful=True,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    return token_pair
