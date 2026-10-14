"""Idempotent HTTP backfill. Source cleanup requires --clear-source."""

import argparse
import asyncio
from uuid import UUID

import httpx
from core.config import get_settings
from core.security import ProfileCipher
from db.postgres import create_engine
from services.profile import ProfileService
from sqlalchemy.ext.asyncio import async_sessionmaker
from unit_of_work.postgres import SQLAlchemyUnitOfWork


async def run(clear_source: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    service = ProfileService(
        lambda: SQLAlchemyUnitOfWork(factory),
        ProfileCipher(
            settings.encryption_keys.get_secret_value(),
            settings.phone_index_key.get_secret_value(),
        ),
    )
    count = 0
    after = None
    try:
        async with httpx.AsyncClient(
            base_url=settings.auth_base_url,
            timeout=settings.http_timeout_seconds,
            headers={
                "X-Service-Token": settings.migration_token.get_secret_value()
            },
        ) as client:
            while True:
                params = {"limit": "100"}
                if after is not None:
                    params["after"] = after
                response = await client.get(
                    "internal/profile-migration/", params=params
                )
                if response.status_code != 200:
                    raise RuntimeError(
                        "Auth export failed; no source cleanup performed"
                    )
                items = response.json()
                if not items:
                    break
                for item in items:
                    count += await service.import_legacy(
                        UUID(item["user_id"]),
                        item["first_name"],
                        item["last_name"],
                    )

                if clear_source:
                    result = await client.post(
                        "internal/profile-migration/clear",
                        json={"items": items},
                    )
                    if result.status_code != 200 or result.json()[
                        "cleared"
                    ] != len(items):
                        raise RuntimeError(
                            "Source cleanup incomplete; rerun the import"
                        )
                after = items[-1]["user_id"]
    finally:
        await engine.dispose()
    print(f"Imported {count} profiles. Source cleanup: {clear_source}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clear-source", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.clear_source))
