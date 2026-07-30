"""CLI-команда создания суперпользователя."""
import asyncio

import typer

from core.config import get_settings
from core.security import hash_password
from db import postgres
from unit_of_work.postgres import SQLAlchemyUnitOfWork

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
        session_factory = postgres.get_session_factory()

        async with SQLAlchemyUnitOfWork(session_factory) as uow:
            existing_user = await uow.users.get_by_login(
                settings.superuser_login,
            )

            if existing_user is not None:
                if existing_user.is_superuser and existing_user.is_active:
                    typer.echo(
                        f'Superuser "{existing_user.login}" already exists.',
                    )
                    return

                existing_user.is_superuser = True
                existing_user.is_active = True

                await uow.users.save(existing_user)
                await uow.commit()

                typer.echo(
                    f'User "{existing_user.login}" promoted to superuser.',
                )
                return

            existing_user_by_email = await uow.users.get_by_email(
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

            superuser = await uow.users.create(
                login=settings.superuser_login,
                email=settings.superuser_email,
                password_hash=hash_password(
                    settings.superuser_password.get_secret_value(),
                ),
                first_name=settings.superuser_first_name,
                last_name=settings.superuser_last_name,
                is_active=True,
                is_superuser=True,
            )

            await uow.commit()

            typer.echo(
                f'Superuser "{superuser.login}" created.',
            )
    finally:
        await postgres.close_postgres()


if __name__ == '__main__':
    app()
