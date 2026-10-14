"""Exercise the real HTTP application, SQL repository, and migration."""

import importlib.util
import os
from pathlib import Path
from uuid import UUID

import httpx
import pytest_asyncio
from alembic.migration import MigrationContext
from alembic.operations import Operations
from auth.client import AuthClient
from core.config import Settings
from cryptography.fernet import Fernet
from db.postgres import Base
from main import create_app
from pydantic import SecretStr

A = UUID("00000000-0000-4000-8000-000000000001")
B = UUID("00000000-0000-4000-8000-000000000002")
STAFF = UUID("00000000-0000-4000-8000-000000000003")


def migrate(connection):
    path = Path(__file__).parents[2] / "alembic/versions/0001_profiles.py"
    spec = importlib.util.spec_from_file_location("profile_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with Operations.context(MigrationContext.configure(connection)):
        module.upgrade()


@pytest_asyncio.fixture
async def api(tmp_path):
    settings = Settings(
        _env_file=None,
        postgres_password=SecretStr("test-password"),
        database_url=os.getenv(
            "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db"
        ),
        encryption_keys=SecretStr(Fernet.generate_key().decode()),
        phone_index_key=SecretStr(Fernet.generate_key().decode()),
        notification_token=SecretStr("worker-token-" + "x" * 32),
        migration_token=SecretStr("migration-token-" + "x" * 32),
    )
    identities = {
        "a": {"id": str(A), "is_active": True},
        "b": {"id": str(B), "is_active": True},
        "staff": {
            "id": str(STAFF),
            "is_active": True,
            "roles": [{"permissions": [{"code": "profiles:read"}]}],
        },
        "disabled": {"id": str(A), "is_active": False},
    }

    def auth(request):
        token = request.headers.get("authorization", "").removeprefix(
            "Bearer "
        )
        if token == "unavailable":
            return httpx.Response(503)
        if token == "bad-contract":
            return httpx.Response(200, json={"id": "invalid"})
        if token not in identities:
            return httpx.Response(401)
        return httpx.Response(200, json=identities[token])

    app = create_app(settings, auth_transport=httpx.MockTransport(auth))
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(migrate)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(auth), base_url="http://auth/api/v1/"
        ) as auth_http:
            app.state.auth_client = AuthClient(auth_http)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://profiles",
            ) as client:
                yield client, app, identities
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
