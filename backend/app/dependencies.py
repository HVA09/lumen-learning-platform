"""
Dependencies مشتركة بين المسارات: المستخدم الحالي، وصلاحيات الأدوار (admin / معلّم)
"""
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.cookies import ACCESS_COOKIE_NAME, verify_csrf_request
from app.auth.security import decode_token
from app.database import get_db
from app.logging_config import get_logger
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole

logger = get_logger("dependencies")

# tokenUrl هنا لأغراض توثيق Swagger فقط — الدخول الفعلي عبر /auth/login بصيغة JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate either a bearer token or a secure browser session cookie."""
    request.state.auth_session = None
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
    using_bearer_token = bool(token)
    if cookie_token and request.method not in ("GET", "HEAD", "OPTIONS"):
        # Cookie-authenticated unsafe requests must prove same-origin intent.
        if not token:
            verify_csrf_request(request)
    token = token or cookie_token
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صالحة",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not isinstance(token, str) or not token:
        raise credentials_error

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_error
        user_id = int(payload.get("sub"))
        token_version = payload.get("ver", 0)
    except (JWTError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or token_version != user.token_version
    ):
        raise credentials_error

    session_id = payload.get("sid")
    if session_id:
        auth_session = db.get(AuthSession, session_id)
        now = datetime.now(timezone.utc)
        if (
            auth_session is None
            or auth_session.user_id != user.id
            or auth_session.revoked_at is not None
            or auth_session.expires_at <= now
        ):
            raise credentials_error
        request.state.auth_session = auth_session
    elif not using_bearer_token:
        # Browser cookies issued by the new flow must always be session-bound.
        # Legacy stateless tokens remain accepted only via explicit Bearer auth.
        raise credentials_error

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Authorization: يسمح فقط لمستخدم بدور admin"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء يتطلب صلاحية admin",
        )
    return current_user


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Authorization: يسمح للمعلّم أو admin — إنشاء الواجبات وتقييمها وإدارة الدروس والأسئلة"""
    if current_user.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="هذا الإجراء للمعلّمين فقط",
        )
    return current_user
