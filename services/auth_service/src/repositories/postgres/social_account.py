"""PostgreSQL-репозиторий социальных аккаунтов."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.role import Role
from models.social_account import SocialAccount
from models.user import User
from repositories.interfaces.social_account import (
    SocialAccountRepository,
)


class PostgresSocialAccountRepository(
    SocialAccountRepository,
):
    """Реализует операции с социальными аккаунтами в PostgreSQL."""
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        """Сохранет PostgreSQL-сессию."""
        self.session = session

    async def get_by_provider_identity(
        self,
        *,
        provider: str,
        provider_user_id: str,
    ) -> SocialAccount | None:
        """Возвращает социальный аккаунт с локальным пользователем."""
        statement = (
            select(SocialAccount)
            .options(
                selectinload(
                    SocialAccount.user,
                )
                .selectinload(
                    User.roles,
                )
                .selectinload(
                    Role.permissions,
                ),
            )
            .where(
                SocialAccount.provider == provider,
                SocialAccount.provider_user_id
                == provider_user_id,
            )
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        email: str | None = None,
    ) -> SocialAccount:
        """Создаёт связь пользователя с OAuth-провайдером."""
        social_account = SocialAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            email=email,
        )

        self.session.add(social_account)
        await self.session.flush()

        return social_account
