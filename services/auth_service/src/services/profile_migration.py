"""Explicit copy-then-clear migration of legacy personal data."""

from __future__ import annotations

from uuid import UUID

from api.v1.schemas.profile_migration import LegacyProfile
from cache.base import Cache
from services.cache_keys.users import get_user_cache_key
from unit_of_work.base import UnitOfWorkFactory


class ProfileMigrationService:
    def __init__(self, uow: UnitOfWorkFactory, cache: Cache) -> None:
        self.uow = uow
        self.cache = cache

    async def list_profiles(
        self, after: UUID | None, limit: int
    ) -> list[LegacyProfile]:
        async with self.uow() as uow:
            users = await uow.users.list_legacy_profiles(after, limit)
            return [
                LegacyProfile(
                    user_id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                )
                for user in users
            ]

    async def clear(self, items: list[LegacyProfile]) -> int:
        cleared = []
        async with self.uow() as uow:
            for item in items:
                user = await uow.users.get_by_id(item.user_id)
                if user is None:
                    continue
                if (user.first_name, user.last_name) == (
                    item.first_name,
                    item.last_name,
                ):
                    user.first_name = None
                    user.last_name = None
                    await uow.users.save(user)
                    cleared.append(user.id)
            await uow.commit()
        for user_id in cleared:
            await self.cache.delete(get_user_cache_key(user_id))
        return len(cleared)
