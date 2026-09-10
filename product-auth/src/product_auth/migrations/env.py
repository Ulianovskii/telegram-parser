import asyncio

from alembic import context
from product_auth.models import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config


def migrate(connection):
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table="auth_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        target_metadata=Base.metadata,
        version_table="auth_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    asyncio.run(online())
