"""SQLAlchemy-модель permission."""

from __future__ import annotations

from typing import TYPE_CHECKING

from db.postgres import Base
from models.association import role_permissions
from models.entity import TimestampMixin, UUIDMixin
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.role import Role


class Permission(UUIDMixin, TimestampMixin, Base):
    """Право доступа."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    roles: Mapped[list[Role]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )
