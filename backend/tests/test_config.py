import pytest
from pydantic import ValidationError

from app.config import Settings
from app.database import normalize_database_url


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
    settings = _production_settings(LTI_TARGET_LINK_URI="https://api.example.com/lti/launch")
    assert settings.DEBUG is False
    assert settings.ENVIRONMENT == "production"


def test_production_rejects_debug_mode():
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        _production_settings(DEBUG=True)


def test_production_rejects_placeholder_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        _production_settings(JWT_SECRET_KEY="change_me_to_a_long_random_secret")


def test_production_rejects_http_cors_origins():
    with pytest.raises(ValidationError, match="HTTPS origin"):
        _production_settings(CORS_ORIGINS=["http://learn.example.com"])



def test_postgresql_urls_select_installed_psycopg2_driver():
    assert normalize_database_url("postgresql://user:pass@db:5432/lumen") == (
        "postgresql+psycopg2://user:pass@db:5432/lumen"
    )
    assert normalize_database_url("postgres://user:pass@db:5432/lumen") == (
        "postgresql+psycopg2://user:pass@db:5432/lumen"
    )
    assert normalize_database_url("postgresql+psycopg://user:pass@db:5432/lumen") == (
        "postgresql+psycopg2://user:pass@db:5432/lumen"
    )
