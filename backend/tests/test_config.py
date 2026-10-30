import pytest
from pydantic import ValidationError

from app.config import Settings


def _production_settings(**overrides):
    values = {
        "DATABASE_URL": "postgresql://postgres:postgres@localhost:5432/lumen",
        "JWT_SECRET_KEY": "e" * 64,
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "FRONTEND_URL": "https://learn.example.com",
        "CORS_ORIGINS": ["https://learn.example.com"],
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_accept_secure_values():
    settings = _production_settings(
        LTI_ALLOWED_TARGET_LINK_URIS=["https://api.example.com/lti/launch"]
    )
    assert settings.DEBUG is False
    assert settings.ENVIRONMENT == "production"


def test_production_rejects_debug_mode():
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        _production_settings(DEBUG=True)


def test_production_rejects_placeholder_or_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _production_settings(JWT_SECRET_KEY="change_me_to_a_long_random_secret")
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _production_settings(JWT_SECRET_KEY="short")


def test_production_rejects_http_or_wildcard_cors_origins():
    with pytest.raises(ValidationError, match="HTTPS origin"):
        _production_settings(CORS_ORIGINS=["http://learn.example.com"])
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        _production_settings(CORS_ORIGINS=["*"])


def test_production_requires_https_frontend_url():
    with pytest.raises(ValidationError, match="FRONTEND_URL"):
        _production_settings(FRONTEND_URL="http://learn.example.com")


def test_production_requires_https_lti_allowlist_entries():
    with pytest.raises(ValidationError, match="LTI target URI"):
        _production_settings(
            LTI_ALLOWED_TARGET_LINK_URIS=["http://api.example.com/lti/launch"]
        )
