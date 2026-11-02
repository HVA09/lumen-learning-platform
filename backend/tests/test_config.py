import pytest
from cryptography.fernet import Fernet
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
        "TOTP_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
        "SMTP_HOST": "smtp.lumen.test",
        "SMTP_FROM_EMAIL": "noreply@lumen.test",
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



def test_production_requires_totp_encryption_key():
    with pytest.raises(ValidationError, match="TOTP_ENCRYPTION_KEY is required"):
        _production_settings(TOTP_ENCRYPTION_KEY="")


def test_production_rejects_invalid_totp_encryption_key():
    with pytest.raises(ValidationError, match="valid URL-safe Fernet key"):
        _production_settings(TOTP_ENCRYPTION_KEY="not-a-fernet-key")



def test_production_requires_smtp_host():
    with pytest.raises(ValidationError, match="SMTP_HOST is required"):
        _production_settings(SMTP_HOST="")



def test_production_requires_smtp_tls():
    with pytest.raises(ValidationError, match="SMTP_USE_TLS must be enabled"):
        _production_settings(SMTP_USE_TLS=False)



def test_production_rejects_placeholder_smtp_sender():
    with pytest.raises(ValidationError, match="SMTP_FROM_EMAIL"):
        _production_settings(SMTP_FROM_EMAIL="noreply@example.com")



def test_production_requires_complete_smtp_credentials():
    with pytest.raises(ValidationError, match="configured together"):
        _production_settings(SMTP_USER="smtp-user", SMTP_PASSWORD="")



def test_nginx_upload_limit_allows_multipart_overhead():
    from pathlib import Path
    import re

    nginx_config = Path(__file__).resolve().parents[1] / "nginx" / "nginx.conf"
    content = nginx_config.read_text(encoding="utf-8")
    match = re.search(r"client_max_body_size\s+(\d+)m\s*;", content)
    assert match is not None
    assert int(match.group(1)) >= 12
