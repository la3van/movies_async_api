"""Profile records contain encrypted PII and no cross-service foreign keys."""

from datetime import datetime
from uuid import UUID, uuid4

from db.postgres import Base
from sqlalchemy import Boolean, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column


class ProfileRecord(Base):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    pii_ciphertext: Mapped[str] = mapped_column(Text)
    phone_index: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProfileAudit(Base):
    __tablename__ = "profile_audit"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[UUID] = mapped_column(Uuid)
    target_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    request_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class ImportedProfile(Base):
    """Prevents a repeated legacy import from resurrecting deleted PII."""

    __tablename__ = "imported_profiles"

    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
