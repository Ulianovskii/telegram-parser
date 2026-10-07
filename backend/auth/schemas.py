# schemas.py — форматы данных, которые принимает и возвращает API авторизации.

from pydantic import BaseModel, ConfigDict, Field


# Тело запроса POST /api/auth/login.
class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


# Безопасное представление пользователя для frontend.
# password_hash сюда намеренно не входит.
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str

# Ответ после успешного входа.
# CSRF-токен frontend будет передавать при изменяющих запросах.
class LoginResponse(BaseModel):
    user: UserResponse
    csrf_token: str