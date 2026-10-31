"""Secure HttpOnly cookie helpers for browser sessions."""
from fastapi import Response

from app.config import settings


def _production_cookie_mode() -> bool:
    return settings.ENVIRONMENT.strip().lower() == "production"


def access_cookie_name() -> str:
    prefix = "__Host-" if _production_cookie_mode() else ""
    return f"{prefix}lumen_access"


def refresh_cookie_name() -> str:
    prefix = "__Host-" if _production_cookie_mode() else ""
    return f"{prefix}lumen_refresh"


def csrf_cookie_name() -> str:
    prefix = "__Host-" if _production_cookie_mode() else ""
    return f"{prefix}lumen_csrf"


def _cookie_options() -> dict:
    return {
        "secure": _production_cookie_mode(),
        "samesite": settings.AUTH_COOKIE_SAMESITE.lower(),
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    options = _cookie_options()
    response.set_cookie(
        key=access_cookie_name(),
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        httponly=True,
        **options,
    )
    response.set_cookie(
        key=refresh_cookie_name(),
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh",
        httponly=True,
        **options,
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=csrf_cookie_name(),
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
        httponly=True,
        **_cookie_options(),
    )


def clear_auth_cookies(response: Response) -> None:
    options = _cookie_options()
    response.delete_cookie(
        key=access_cookie_name(), path="/", httponly=True, **options
    )
    response.delete_cookie(
        key=refresh_cookie_name(), path="/auth/refresh", httponly=True, **options
    )
