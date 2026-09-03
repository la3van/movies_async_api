"""Security-утилиты auth-сервиса."""

import hashlib
import secrets

from passlib.context import CryptContext

password_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Возвращает bcrypt-хеш пароля."""
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль по его bcrypt-хешу."""
    return password_context.verify(password, password_hash)


def generate_secure_token() -> str:
    """Генерирует криптографически стойкий случайный токен."""
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """Возвращает SHA-256 хеш токена."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
