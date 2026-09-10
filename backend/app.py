# app.py — основной FastAPI-сервер продукта.
# Подключает PostgreSQL и готовый модуль авторизации.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from product_auth import AuthModule, AuthSettings


# Загружает настройки авторизации из переменных окружения.
settings = AuthSettings()

# Создаёт средство подключения к PostgreSQL.
engine = create_async_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
)

# Создаёт фабрику временных SQLAlchemy-сессий для запросов к базе.
session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

# Создаёт готовый модуль авторизации.
auth = AuthModule(settings, session_factory)


# При остановке сервера закрывает подключения к PostgreSQL.
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


# Создаёт основной FastAPI-сервер.
app = FastAPI(lifespan=lifespan)

# Подключает маршруты /auth/telegram/start, /callback, /me и /logout.
app.include_router(auth.router)


# Простой адрес для проверки, что сервер запущен.
@app.get("/health")
async def health():
    return {"status": "ok"}