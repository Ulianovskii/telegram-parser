# create_user.py — создание пользователя вручную через терминал.

import argparse
import asyncio
from datetime import UTC, datetime
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.auth.security import hash_password
from backend.database import engine, session_factory
from backend.models import User


# Создаёт пользователя, если указанный логин ещё не занят.
async def create_user(username: str) -> None:
    # Логины храним в нижнем регистре, чтобы Andrew и andrew
    # не стали двумя разными пользователями.
    normalized_username = username.strip().lower()

    if not normalized_username:
        raise ValueError("Логин не может быть пустым")

    # getpass читает пароль без отображения символов в терминале.
    password = getpass("Пароль: ")
    password_confirmation = getpass("Повторите пароль: ")

    if not password:
        raise ValueError("Пароль не может быть пустым")

    if password != password_confirmation:
        raise ValueError("Пароли не совпадают")

    async with session_factory() as database_session:
        existing_user = await database_session.scalar(
            select(User).where(User.username == normalized_username)
        )

        if existing_user is not None:
            raise ValueError(f"Пользователь {normalized_username} уже существует")

        user = User(
            username=normalized_username,
            password_hash=hash_password(password),
            is_active=True,
            created_at=datetime.now(UTC),
        )

        database_session.add(user)

        try:
            await database_session.commit()
        except IntegrityError:
            await database_session.rollback()
            raise ValueError(
                f"Пользователь {normalized_username} уже существует"
            ) from None

    print(f"Пользователь {normalized_username} создан")


# Читает логин из аргумента команды.
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Создать пользователя приложения"
    )
    parser.add_argument("username", help="Логин нового пользователя")
    return parser.parse_args()


# Точка запуска команды python -m backend.create_user.
async def main() -> None:
    arguments = parse_arguments()

    try:
        await create_user(arguments.username)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())