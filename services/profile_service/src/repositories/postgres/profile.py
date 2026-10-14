"""SQLAlchemy implementation; uniqueness is enforced by PostgreSQL."""

from uuid import UUID

from models.profile import ImportedProfile, ProfileAudit, ProfileRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class PostgresProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, user_id: UUID, *, lock: bool = False
    ) -> ProfileRecord | None:
        query = select(ProfileRecord).where(ProfileRecord.user_id == user_id)
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def list(
        self, after: UUID | None, limit: int
    ) -> list[ProfileRecord]:
        query = (
            select(ProfileRecord).order_by(ProfileRecord.user_id).limit(limit)
        )
        if after is not None:
            query = query.where(ProfileRecord.user_id > after)
        return list((await self.session.scalars(query)).all())

    async def add(self, profile: ProfileRecord) -> None:
        self.session.add(profile)
        await self.session.flush()

    async def delete(self, profile: ProfileRecord) -> None:
        await self.session.delete(profile)

    async def was_imported(self, user_id: UUID) -> bool:
        return await self.session.get(ImportedProfile, user_id) is not None

    async def mark_imported(self, user_id: UUID) -> None:
        if not await self.was_imported(user_id):
            self.session.add(ImportedProfile(user_id=user_id))

    async def audit(
        self, actor: UUID, target: UUID | None, action: str, request_id: str
    ) -> None:
        self.session.add(
            ProfileAudit(
                actor_id=actor,
                target_id=target,
                action=action,
                request_id=request_id[:128],
            )
        )
