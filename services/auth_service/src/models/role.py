"""SQLAlchemy-модель роли."""

from __future__ import annotations

from typing import TYPE_CHECKING

from db.postgres import Base
from models.association import role_permissions, user_roles
from models.entity import TimestampMixin, UUIDMixin
from sqlalchemy import Boolean, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.permission import Permission
    from models.user import User


class Role(UUIDMixin, TimestampMixin, Base):
    """Роль пользователя."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    users: Mapped[list[User]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )

    permissions: Mapped[list[Permission]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
