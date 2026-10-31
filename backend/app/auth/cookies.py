"""Secure browser session cookies and double-submit CSRF protection."""

import secrets
from hmac import compare_digest

from fastapi import HTTPException, Request, Response, status

from app.config import settings

ACCESS_COOKIE_NAME = "lumen_access"
REFRESH_COOKIE_NAME = "lumen_refresh"
CSRF_COOKIE_NAME = "lumen_csrf"
CSRF_HEADER_NAME = "X-CSRF-Token"


def _cookie_security() -> tuple[bool, str]:
    secure = settings.ENVIRONMENT.strip().lower() == "production"
    same_site = settings.AUTH_COOKIE_SAMESITE
    if same_site == "none" and not secure:
        raise RuntimeError("SameSite=None authentication cookies require HTTPS")
    return secure, same_site


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str) -> None:
    secure, same_site = _cookie_security()
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=secure,
        samesite=same_site,
        path="/",
    )


def issue_csrf_cookie(request: Request, response: Response) -> str:
    token = request.cookies.get(CSRF_COOKIE_NAME)
    if not token or len(token) < 32:
        token = create_csrf_token()
    set_csrf_cookie(response, token)
    return token


def verify_csrf_request(request: Request) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    if (
        not cookie_token
        or not header_token
        or not compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    secure, same_site = _cookie_security()
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/auth",
    )
    set_csrf_cookie(response, csrf_token)


def clear_auth_cookies(response: Response) -> None:
    secure, same_site = _cookie_security()
    response.delete_cookie(
        key=ACCESS_COOKIE_NAME,
        path="/",
        secure=secure,
        httponly=True,
        samesite=same_site,
    )
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/auth",
        secure=secure,
        httponly=True,
        samesite=same_site,
    )
