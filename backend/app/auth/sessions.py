"""Create and validate opaque, database-backed browser sessions."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from sqlalchemy.orm import Session

from app.auth.security import create_access_token, create_refresh_token
from app.config import settings
from app.models.auth_session import AuthSession
from app.models.user import User


def hash_refresh_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def create_browser_session(db: Session, user: User) -> tuple[str, str, AuthSession]:
    """Create an independent session for this browser/device."""
    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(32)
    refresh_jti = secrets.token_urlsafe(32)
    session = AuthSession(
        id=session_id,
        user_id=user.id,
        refresh_jti_hash=hash_refresh_jti(refresh_jti),
        created_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    access_token = create_access_token(
        user.id, user.token_version, session_id=session_id
    )
    refresh_token = create_refresh_token(
        user.id,
        user.token_version,
        session_id=session_id,
        jti=refresh_jti,
    )
    return access_token, refresh_token, session


def refresh_jti_matches(session: AuthSession, presented_jti: str) -> bool:
    return compare_digest(session.refresh_jti_hash, hash_refresh_jti(presented_jti))
