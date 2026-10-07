# app.py — основной FastAPI-сервер продукта.

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.router import router as auth_router
from backend.database import engine


# При остановке сервера корректно закрывает подключения к PostgreSQL.
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


# Создаёт основной FastAPI-сервер.
app = FastAPI(lifespan=lifespan)


# Разрешает отдельному React-приложению обращаться к backend.
# allow_credentials нужен для передачи HttpOnly cookie.
frontend_origins = os.getenv(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://localhost:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключает маршруты, начинающиеся с /api/auth.
app.include_router(auth_router)


# Проверяет, что backend запущен.
@app.get("/health")
async def health():
    return {"status": "ok"}