"""Re-encrypt in batches using the first ENCRYPTION_KEYS key."""

import asyncio

from core.config import get_settings
from core.security import ProfileCipher
from db.postgres import create_engine
from models.profile import ProfileRecord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker


async def run() -> None:
    settings = get_settings()
    cipher = ProfileCipher(
        settings.encryption_keys.get_secret_value(),
        settings.phone_index_key.get_secret_value(),
    )
    engine = create_engine(settings)
    factory = async_sessionmaker(engine)
    after = None
    count = 0
    try:
        while True:
            async with factory() as session, session.begin():
                query = (
                    select(ProfileRecord)
                    .order_by(ProfileRecord.user_id)
                    .limit(100)
                    .with_for_update()
                )
                if after is not None:
                    query = query.where(ProfileRecord.user_id > after)
                records = list((await session.scalars(query)).all())
                if not records:
                    break
                for record in records:
                    record.pii_ciphertext = cipher.rotate(
                        record.pii_ciphertext
                    )
                after = records[-1].user_id
                count += len(records)
    finally:
        await engine.dispose()
    print(f"Re-encrypted {count} profiles. Phone index key unchanged.")


if __name__ == "__main__":
    asyncio.run(run())
