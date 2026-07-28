"""SQLAlchemy-модель социального аккаунта."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.postgres import Base
from models.entity import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.user import User


class SocialAccount(UUIDMixin, TimestampMixin, Base):
    """Связь локального пользователя с OAuth-провайдером."""
    __tablename__ = 'social_accounts'

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey(
            'users.id',
            ondelete='CASCADE',
        ),
        index=True,
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    user: Mapped[User] = relationship(
        back_populates='social_accounts',
    )

    __table_args__ = (
        UniqueConstraint(
            'provider',
            'provider_user_id',
            name=(
                'uq_social_accounts_'
                'provider_provider_user_id'
            ),
        ),
    )
