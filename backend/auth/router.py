# router.py — HTTP-эндпоинты входа и управления авторизацией.

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.schemas import LoginRequest, LoginResponse, UserResponse
from backend.auth.security import (
    generate_token,
    hash_token,
    verify_password,
)
from backend.dependencies import get_database_session
from backend.models import User, UserSession


# Все маршруты этого файла начинаются с /api/auth.
router = APIRouter(prefix="/api/auth", tags=["auth"])

# Сессия действует 30 дней с момента входа.
SESSION_LIFETIME = timedelta(days=30)

# Имя HttpOnly cookie, в которой браузер хранит сессионный токен.
SESSION_COOKIE_NAME = "product_session"


# Проверяет логин и пароль, создаёт сессию и устанавливает cookie.
@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    database_session: Annotated[
        AsyncSession,
        Depends(get_database_session),
    ],
) -> LoginResponse:
    normalized_username = login_data.username.strip().lower()

    user = await database_session.scalar(
        select(User).where(User.username == normalized_username)
    )

    # Используем одно сообщение для неверного логина и неверного пароля,
    # чтобы не раскрывать существование конкретного пользователя.
    if (
        user is None
        or not user.is_active
        or not verify_password(user.password_hash, login_data.password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    # Открытые токены получает браузер, а в PostgreSQL сохраняются их хеши.
    session_token = generate_token()
    csrf_token = generate_token()
    now = datetime.now(UTC)
    expires_at = now + SESSION_LIFETIME

    user_session = UserSession(
        token_hash=hash_token(session_token),
        user_id=user.id,
        csrf_token_hash=hash_token(csrf_token),
        expires_at=expires_at,
        created_at=now,
    )

    database_session.add(user_session)
    await database_session.commit()

    # HttpOnly запрещает JavaScript читать сессионный токен.
    # secure=False используется только для локального HTTP.
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )

    return LoginResponse(
        user=UserResponse.model_validate(user),
        csrf_token=csrf_token,
    )