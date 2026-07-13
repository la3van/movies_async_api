"""SQLAlchemy-модель истории входов."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, false
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.postgres import Base
from models.entity import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from models.user import User


class LoginHistory(UUIDMixin, TimestampMixin, Base):
    """Запись истории входа пользователя."""
    __tablename__ = 'login_history'

    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        index=True,
        nullable=True,
    )

    login: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    is_successful: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user: Mapped[User | None] = relationship(
        back_populates='login_history',
    )
