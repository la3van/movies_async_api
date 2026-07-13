"""CLI-команда создания суперпользователя."""
import asyncio

import typer

from core.config import get_settings
from core.security import hash_password
from db import postgres
from repositories.postgres.user import PostgresUserRepository

app = typer.Typer(
    help='Команды управления суперпользователем auth-сервиса.',
)


@app.command()
def create_superuser() -> None:
    """Создаёт суперпользователя из настроек окружения."""
    asyncio.run(_create_superuser())


async def _create_superuser() -> None:
    """Создаёт суперпользователя из переменных окружения."""

    settings = get_settings()

    await postgres.init_postgres()

    try:
        if postgres.async_session_factory is None:
            raise RuntimeError('PostgreSQL session factory is not initialized')

        async with postgres.async_session_factory() as session:
            user_repository = PostgresUserRepository(session)

            existing_user = await user_repository.get_by_login(
                settings.superuser.login,
            )
            if existing_user is not None:
                if existing_user.is_superuser and existing_user.is_active:
                    typer.echo(
                        f'Superuser "{existing_user.login}" already exists.'
                    )
                    return

                existing_user.is_superuser = True
                existing_user.is_active = True

                session.add(existing_user)
                await session.commit()

                typer.echo(
                    f'User "{existing_user.login}" promoted to superuser.',
                )
                return

            existing_user_by_email = await user_repository.get_by_email(
                settings.superuser_email,
            )
            if existing_user_by_email is not None:
                typer.echo(
                    (
                        f'User with email "{settings.superuser_email}" '
                        'already exists with another login.'
                    ),
                    err=True,
                )
                raise typer.Exit(code=1)

            superuser = await user_repository.create(
                login=settings.superuser_login,
                email=settings.superuser_email,
                password_hash=hash_password(settings.superuser_password),
                first_name=settings.superuser_first_name,
                last_name=settings.superuser_last_name,
                is_active=True,
                is_superuser=True,
            )

            await session.commit()

            typer.echo(f'Superuser "{superuser.login}" created.')

    finally:
        await postgres.close_postgres()


if __name__ == '__main__':
    app()
