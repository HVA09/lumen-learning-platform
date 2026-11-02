"""
تشفير كلمات المرور، وإنشاء/فك تشفير JWT tokens
"""
from datetime import datetime, timedelta, timezone
import secrets

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


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: str,
    token_version: int = 0,
    session_id: str | None = None,
    jti: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        # Missing version claims on older tokens are treated as version 0.
        "ver": token_version,
    }
    if token_type in {"access", "refresh"}:
        # JWT NumericDate timestamps have second precision; a unique jti keeps
        # rapid token refreshes distinct even within the same second.
        payload["jti"] = jti or secrets.token_urlsafe(24)
    if session_id is not None:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: int,
    token_version: int = 0,
    session_id: str | None = None,
) -> str:
    return _create_token(
        str(user_id),
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
        token_version,
        session_id=session_id,
    )


def create_refresh_token(
    user_id: int,
    token_version: int = 0,
    session_id: str | None = None,
    jti: str | None = None,
) -> str:
    return _create_token(
        str(user_id),
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh",
        token_version,
        session_id=session_id,
        jti=jti,
    )


def create_email_verification_token(user_id: int, token_version: int = 0) -> str:
    return _create_token(str(user_id), timedelta(hours=24), "email_verify", token_version)


def create_password_reset_token(user_id: int, token_version: int = 0) -> str:
    return _create_token(str(user_id), timedelta(hours=1), "password_reset", token_version)


def decode_token(token: str) -> dict:
    """يرمي jose.JWTError لو التوكن غير صالح أو منتهي — تُمسك في dependencies.py"""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
