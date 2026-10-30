"""
تشفير كلمات المرور، وإنشاء/فك تشفير JWT tokens
"""
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.config import settings
from app.password_policy import fits_bcrypt_password, validate_bcrypt_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # Reject overlong input even when called outside a Pydantic request schema.
    validate_bcrypt_password(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Never allow a password longer than bcrypt's limit to match by prefix truncation.
    if not fits_bcrypt_password(plain_password):
        return False
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _create_token(
        str(user_id), timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access"
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id), timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh"
    )


def create_email_verification_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(hours=24), "email_verify")


def create_password_reset_token(user_id: int) -> str:
    return _create_token(str(user_id), timedelta(hours=1), "password_reset")


def decode_token(token: str) -> dict:
    """يرمي jose.JWTError لو التوكن غير صالح أو منتهي — تُمسك في dependencies.py"""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
