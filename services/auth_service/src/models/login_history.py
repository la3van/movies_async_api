"""SQLAlchemy-модель истории входов."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from db.postgres import Base
from models.entity import TimestampMixin, UUIDMixin
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    desc,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.user import User


class LoginHistory(UUIDMixin, TimestampMixin, Base):
    """Запись истории входа пользователя."""

    __tablename__ = "login_history"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
        nullable=False,
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    login: Mapped[str] = mapped_column(
        String(255),
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
        back_populates="login_history",
    )

    __table_args__ = (
        Index(
            "ix_login_history_user_created_at_id",
            "user_id",
            desc("created_at"),
            desc("id"),
        ),
        Index(
            "ix_login_history_login_created_at_id",
            "login",
            desc("created_at"),
            desc("id"),
        ),
        {
            "postgresql_partition_by": "RANGE (created_at)",
        },
    )
