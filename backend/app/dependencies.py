"""
Dependencies مشتركة بين المسارات: المستخدم الحالي، وصلاحيات الأدوار (admin / معلّم)
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.cookies import access_cookie_name
from app.auth.security import decode_token
from app.database import get_db
from app.logging_config import get_logger
from app.models.user import User, UserRole

logger = get_logger("dependencies")

# tokenUrl هنا لأغراض توثيق Swagger فقط — الدخول الفعلي عبر /auth/login بصيغة JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate bearer tokens for API clients or HttpOnly cookies for browsers."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="بيانات الدخول غير صالحة",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = token or request.cookies.get(access_cookie_name())
    if not token:
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
