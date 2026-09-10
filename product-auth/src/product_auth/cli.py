# cli.py — точка входа для служебных команд модуля авторизации,
# которые запускаются из терминала, а не через браузер или HTTP API.

import argparse
import asyncio
import os
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from .models import LoginFlow, Session


def main():
    parser = argparse.ArgumentParser(description="Manage this product's auth schema")
    parser.add_argument("command", choices=["migrate", "cleanup"])
    args = parser.parse_args()
    load_dotenv()
    url = os.environ.get("AUTH_DATABASE_URL", "sqlite+aiosqlite:///./auth.db")
    if args.command == "migrate":
        config = Config()
        config.set_main_option(
            "script_location", str(Path(__file__).parent / "migrations")
        )
        config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        command.upgrade(config, "head")
        print("Auth database migrations applied.")
    else:

        async def cleanup():
            engine = create_async_engine(url)
            async with engine.begin() as connection:
                now = int(time.time())
                await connection.execute(
                    delete(LoginFlow).where(LoginFlow.expires_at <= now)
                )
                await connection.execute(
                    delete(Session).where(Session.expires_at <= now)
                )
            await engine.dispose()

        asyncio.run(cleanup())
        print("Expired auth records removed.")


if __name__ == "__main__":
    main()
