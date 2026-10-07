# database.py — подключение FastAPI-приложения к PostgreSQL.

import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# Получает адрес PostgreSQL из переменной окружения контейнера.
database_url = os.environ["DATABASE_URL"]


# Engine управляет пулом подключений к PostgreSQL.
engine = create_async_engine(
    database_url,
    pool_pre_ping=True,
)


# Фабрика создаёт отдельную SQLAlchemy-сессию для каждого запроса.
session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)