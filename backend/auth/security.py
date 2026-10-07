# security.py — хеширование паролей и работа с безопасными случайными токенами.

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError


# Настраивает Argon2id с безопасными параметрами библиотеки по умолчанию.
password_hasher = PasswordHasher()


# Создаёт необратимый Argon2id-хеш пароля с индивидуальной случайной солью.
def hash_password(password: str) -> str:
    return password_hasher.hash(password)


# Сравнивает введённый пароль с сохранённым хешем.
def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# Создаёт случайный токен, который будет передан браузеру.
def generate_token() -> str:
    return secrets.token_urlsafe(32)


# Создаёт SHA-256-хеш токена для безопасного хранения в PostgreSQL.
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

    