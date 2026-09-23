"""Порционное создание заданий по сохранённой аудитории рассылки."""

import asyncio
import logging
from uuid import UUID

import httpx
from core.config import get_settings
from core.database import create_engine
from core.health import beat, unready
from core.runtime import pause, supervise
from pydantic import BaseModel
from repositories.postgres.catalog import Catalog
from sqlalchemy import text


class AudiencePage(BaseModel):
    """Страница UUID получателей из снимка аудитории Auth."""

    users: list[UUID]


async def run(stop: asyncio.Event) -> None:
    """Разворачивает готовые кампании порциями из снимка аудитории Auth."""
    settings = get_settings()
    if not settings.internal_token.get_secret_value():
        raise RuntimeError("INTERNAL_TOKEN required")
    engine = create_engine(settings)
    catalog = Catalog(engine, settings)
    try:
        async with httpx.AsyncClient(
            base_url=settings.auth_base_url,
            timeout=20,
            headers={
                "X-Service-Token": settings.internal_token.get_secret_value()
            },
        ) as client:
            while not stop.is_set():
                try:
                    async with engine.begin() as conn:
                        row = (
                            (
                                await conn.execute(
                                    text("""
                            SELECT * FROM campaigns WHERE
state!='expanded' AND scheduled_at<=now()
                            ORDER BY scheduled_at FOR UPDATE SKIP
LOCKED LIMIT 1
""")
                                )
                            )
                            .mappings()
                            .first()
                        )
                        if row is not None:
                            url = "internal/notifications/audiences/" + str(
                                row["id"]
                            )
                            response = await client.post(url)
                            response.raise_for_status()
                            params = {
                                "limit": str(settings.audience_page_size)
                            }
                            if row["cursor"]:
                                params["after"] = str(row["cursor"])
                            response = await client.get(url, params=params)
                            response.raise_for_status()
                            users = AudiencePage.model_validate(
                                response.json()
                            ).users
                            if users != sorted(set(users)) or (
                                users
                                and row["cursor"]
                                and users[0] <= row["cursor"]
                            ):
                                raise ValueError("Invalid audience page")
                            await catalog.expand_page(conn, row, users)
                    beat()
                    await pause(stop, settings.poll_seconds)
                except Exception:
                    unready()
                    logging.getLogger(__name__).error(
                        "Campaign expansion failed"
                    )
                    await pause(stop, settings.poll_seconds)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(supervise(run))
