"""SQLAlchemy-модель пользователя."""

from __future__ import annotations

from typing import TYPE_CHECKING

from db.postgres import Base
from models.association import user_roles
from models.entity import TimestampMixin, UUIDMixin
from sqlalchemy import Boolean, String, false, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.login_history import LoginHistory
    from models.refresh_session import RefreshSession
    from models.role import Role
    from models.social_account import SocialAccount


class User(UUIDMixin, TimestampMixin, Base):
    """Пользователь auth-сервиса."""

    __tablename__ = "users"

    login: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    refresh_sessions: Mapped[list[RefreshSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    login_history: Mapped[list[LoginHistory]] = relationship(
        back_populates="user",
    )

    social_accounts: Mapped[list[SocialAccount]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
