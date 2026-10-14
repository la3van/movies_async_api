"""Profile use cases with atomic writes and audited private reads."""

from datetime import datetime, timezone
from uuid import UUID

from api.v1.schemas.profiles import (
    ProfileCreate,
    ProfilePage,
    ProfileResponse,
    ProfileUpdate,
)
from core.security import ProfileCipher
from models.profile import ProfileRecord
from services.exceptions import PhoneTaken, ProfileExists, ProfileNotFound
from sqlalchemy.exc import IntegrityError
from unit_of_work.base import UnitOfWorkFactory


class ProfileService:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, cipher: ProfileCipher
    ) -> None:
        self._uow = uow_factory
        self._cipher = cipher

    def _response(self, record: ProfileRecord) -> ProfileResponse:
        data = self._cipher.decrypt(record.user_id, record.pii_ciphertext)
        return ProfileResponse(
            user_id=record.user_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            middle_name=data.get("middle_name"),
            phone=data.get("phone"),
            phone_verified_at=record.phone_verified_at,
            marketing_consent=record.marketing_consent,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    async def create(
        self, user_id: UUID, data: ProfileCreate, request_id: str
    ) -> ProfileResponse:
        try:
            async with self._uow() as uow:
                if await uow.profiles.get(user_id) is not None:
                    raise ProfileExists
                pii = {
                    "first_name": data.first_name,
                    "last_name": data.last_name,
                    "middle_name": data.middle_name,
                    "phone": data.phone,
                }
                now = datetime.now(timezone.utc)
                record = ProfileRecord(
                    user_id=user_id,
                    pii_ciphertext=self._cipher.encrypt(user_id, pii),
                    phone_index=self._cipher.phone_index(data.phone),
                    marketing_consent=data.marketing_consent,
                    created_at=now,
                    updated_at=now,
                )
                await uow.profiles.add(record)
                await uow.profiles.audit(
                    user_id, user_id, "profile.create", request_id
                )
                result = self._response(record)
                await uow.commit()
                return result
        except IntegrityError as exc:
            async with self._uow() as uow:
                if await uow.profiles.get(user_id) is not None:
                    raise ProfileExists from exc
            raise PhoneTaken from exc

    async def get(
        self,
        user_id: UUID,
        actor: UUID,
        request_id: str,
        *,
        action: str = "profile.read",
    ) -> ProfileResponse:
        async with self._uow() as uow:
            record = await uow.profiles.get(user_id)
            if record is None:
                raise ProfileNotFound
            result = self._response(record)
            await uow.profiles.audit(actor, user_id, action, request_id)
            await uow.commit()
            return result

    async def list(
        self, actor: UUID, after: UUID | None, limit: int, request_id: str
    ) -> ProfilePage:
        async with self._uow() as uow:
            records = await uow.profiles.list(after, limit + 1)
            items = [self._response(record) for record in records[:limit]]

            for item in items:
                if item.phone:
                    item.phone = "***" + item.phone[-4:]
            await uow.profiles.audit(actor, None, "profile.list", request_id)
            await uow.commit()
            return ProfilePage(
                items=items,
                next_cursor=(
                    items[-1].user_id if len(records) > limit else None
                ),
            )

    async def update(
        self, user_id: UUID, data: ProfileUpdate, request_id: str
    ) -> ProfileResponse:
        try:
            async with self._uow() as uow:
                record = await uow.profiles.get(user_id, lock=True)
                if record is None:
                    raise ProfileNotFound
                pii = self._cipher.decrypt(user_id, record.pii_ciphertext)
                for key in ("first_name", "last_name", "middle_name", "phone"):
                    if key in data.model_fields_set:
                        pii[key] = getattr(data, key)
                if "phone" in data.model_fields_set:
                    index = self._cipher.phone_index(data.phone)
                    if index != record.phone_index:
                        record.phone_verified_at = None
                    record.phone_index = index
                if data.marketing_consent is not None:
                    record.marketing_consent = data.marketing_consent
                record.pii_ciphertext = self._cipher.encrypt(user_id, pii)
                record.updated_at = datetime.now(timezone.utc)
                await uow.profiles.audit(
                    user_id, user_id, "profile.update", request_id
                )
                result = self._response(record)
                await uow.commit()
                return result
        except IntegrityError as exc:
            raise PhoneTaken from exc

    async def delete(self, user_id: UUID, request_id: str) -> None:
        async with self._uow() as uow:
            record = await uow.profiles.get(user_id, lock=True)
            if record is None:
                raise ProfileNotFound
            await uow.profiles.delete(record)
            await uow.profiles.mark_imported(user_id)
            await uow.profiles.audit(
                user_id, user_id, "profile.delete", request_id
            )
            await uow.commit()

    async def import_legacy(
        self, user_id: UUID, first_name: str | None, last_name: str | None
    ) -> bool:
        """Preserve user edits and deletion markers on every retry."""
        async with self._uow() as uow:
            if await uow.profiles.was_imported(user_id):
                return False
            created = await uow.profiles.get(user_id) is None
            if created:
                data = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "middle_name": None,
                    "phone": None,
                }
                now = datetime.now(timezone.utc)
                await uow.profiles.add(
                    ProfileRecord(
                        user_id=user_id,
                        pii_ciphertext=self._cipher.encrypt(user_id, data),
                        marketing_consent=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
            await uow.profiles.mark_imported(user_id)
            await uow.profiles.audit(
                user_id, user_id, "profile.import", "legacy-import"
            )
            await uow.commit()
            return created
