"""Фикстуры PostgreSQL функциональных тестов."""

from typing import Any
from uuid import UUID

import asyncpg
import pytest
import pytest_asyncio

from tests.functional.settings import test_settings

TRUNCATE_AUTH_TABLES_QUERY = """
TRUNCATE TABLE
    user_roles,
    role_permissions,
    login_history,
    refresh_sessions,
    users,
    roles,
    permissions
RESTART IDENTITY CASCADE
"""


@pytest_asyncio.fixture(name="postgres_pool", scope="session")
async def postgres_pool():
    """Создаёт пул подключений к PostgreSQL на время тестовой сессии."""
    pool = await asyncpg.create_pool(
        host=test_settings.postgres_host,
        port=test_settings.postgres_port,
        database=test_settings.postgres_db,
        user=test_settings.postgres_user,
        password=test_settings.postgres_password,
        min_size=1,
        max_size=5,
        timeout=test_settings.postgres_connect_timeout,
    )

    yield pool

    await pool.close()


@pytest_asyncio.fixture(name="postgres_clear", autouse=True)
async def postgres_clear(postgres_pool: asyncpg.Pool):
    """Очищает таблицы auth-сервиса до и после каждого теста."""
    await truncate_auth_tables(postgres_pool)

    yield

    await truncate_auth_tables(postgres_pool)


@pytest.fixture(name="pg_fetch")
def pg_fetch(postgres_pool: asyncpg.Pool):
    """Возвращает функцию выполнения SELECT-запроса с несколькими строками."""

    async def inner(
        query: str,
        *args: Any,
    ) -> list[asyncpg.Record]:
        """Выполняет SELECT-запрос и возвращает список строк."""
        async with postgres_pool.acquire() as connection:
            return await connection.fetch(query, *args)

    return inner


@pytest.fixture(name="pg_fetchrow")
def pg_fetchrow(postgres_pool: asyncpg.Pool):
    """Возвращает функцию выполнения SELECT-запроса с одной строкой."""

    async def inner(
        query: str,
        *args: Any,
    ) -> asyncpg.Record | None:
        """Выполняет SELECT-запрос и возвращает одну строку."""
        async with postgres_pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    return inner


@pytest.fixture(name="pg_execute")
def pg_execute(postgres_pool: asyncpg.Pool):
    """Возвращает функцию выполнения SQL-запроса без результата."""

    async def inner(
        query: str,
        *args: Any,
    ) -> str:
        """Выыполняет SQL-запрос."""
        async with postgres_pool.acquire() as connection:
            return await connection.execute(query, *args)

    return inner


@pytest.fixture(name="get_user_by_login")
def get_user_by_login(pg_fetchrow):
    """Возвращает функцию получения пользователя по login."""

    async def inner(login: str) -> asyncpg.Record | None:
        """Возвращает пользоватя по login."""
        return await pg_fetchrow(
            """
            SELECT
                id,
                login,
                email,
                first_name,
                last_name,
                is_active,
                is_superuser,
                created_at,
                updated_at
            FROM users
            WHERE login = $1;
            """,
            login,
        )

    return inner


@pytest.fixture(name="get_user_by_email")
def get_user_by_email(pg_fetchrow):
    """Возвращает функцию получения пользователя по email."""

    async def inner(email: str) -> asyncpg.Record | None:
        """Возвращает пользоватя по email."""
        return await pg_fetchrow(
            """
            SELECT
                id,
                login,
                email,
                first_name,
                last_name,
                is_active,
                is_superuser,
                created_at,
                updated_at
            FROM users
            WHERE email = $1;
            """,
            email,
        )

    return inner


@pytest.fixture(name="promote_user_to_superuser")
def promote_user_to_superuser(pg_execute):
    """Возвращает функцию повышения пользователя до суперпользователя."""

    async def inner(user_id: UUID) -> None:
        """Дулает пользователя активным суперпользователем."""
        await pg_execute(
            """
            UPDATE users
            SET
                is_active = true,
                is_superuser = true
            WHERE id = $1;
            """,
            user_id,
        )

    return inner


@pytest.fixture(name="get_refresh_sessions_by_user_id")
def get_refresh_sessions_by_user_id(pg_fetch):
    """Возвращает функцию получения refresh-сессий пользователя."""

    async def inner(user_id: UUID) -> list[asyncpg.Record]:
        """Возвращает refresh-сессии пользователя."""
        return await pg_fetch(
            """
            SELECT
                id,
                user_id,
                token_hash,
                user_agent,
                ip_address,
                expires_at,
                revoked_at,
                created_at,
                updated_at
            FROM refresh_sessions
            WHERE user_id = $1
            ORDER BY created_at ASC;
            """,
            user_id,
        )

    return inner


@pytest.fixture(name="get_login_history_by_login")
def get_login_history_by_login(pg_fetch):
    """Возвращает функцию получения истории входов по login."""

    async def inner(login: str) -> list[asyncpg.Record]:
        """Возвращает историю входов по login."""
        return await pg_fetch(
            """
            SELECT
                id,
                user_id,
                login,
                is_successful,
                reason,
                user_agent,
                ip_address,
                created_at,
                updated_at
            FROM login_history
            WHERE login = $1
            ORDER BY created_at ASC;
            """,
            login,
        )

    return inner


async def truncate_auth_tables(postgres_pool: asyncpg.Pool) -> None:
    """Очищает таблицы auth-сервиса."""
    async with postgres_pool.acquire() as connection:
        await connection.execute(TRUNCATE_AUTH_TABLES_QUERY)


@pytest.fixture(name="delete_user_by_id")
def delete_user_by_id(pg_execute):
    """Возвращает функцию удаления пользователя по id."""

    async def inner(user_id: str) -> None:
        """Удаляет пользователя из PostgreSQL."""

        await pg_execute(
            """
            DELETE FROM users
            WHERE id = $1::uuid;
            """,
            user_id,
        )

    return inner


@pytest.fixture(name="delete_login_history_by_user_id")
def delete_login_history_by_user_id(pg_execute):
    """Возвращает функцию удаления истории входов пользователя."""

    async def inner(user_id: str) -> None:
        """Удаляет историю входов пользователя из PostgreSQL."""

        await pg_execute(
            """
            DELETE FROM login_history
            WHERE user_id = $1::uuid;
            """,
            user_id,
        )

    return inner


@pytest.fixture(name="delete_permission_by_id")
def delete_permission_by_id(pg_execute):
    """Возвращает функцию удаления permission по id."""

    async def inner(permission_id: str) -> None:
        """Удаляет permission из PostgreSQL."""

        await pg_execute(
            """
            DELETE FROM permissions
            WHERE id = $1::uuid;
            """,
            permission_id,
        )

    return inner


@pytest.fixture(name="delete_role_by_id")
def delete_role_by_id(pg_execute):
    """Возвращает функцию удаления роли по id."""

    async def inner(role_id: str) -> None:
        """Удаляет роль из PostgreSQL."""

        await pg_execute(
            """
            DELETE FROM roles
            WHERE id = $1::uuid;
            """,
            role_id,
        )

    return inner
