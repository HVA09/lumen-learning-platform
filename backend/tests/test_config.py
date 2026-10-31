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
        "MALWARE_SCAN_ENABLED": True,
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


def test_production_requires_malware_scanning():
    with pytest.raises(ValidationError, match="MALWARE_SCAN_ENABLED must be true"):
        _production_settings(MALWARE_SCAN_ENABLED=False)


def test_production_requires_valid_clamav_endpoint():
    with pytest.raises(ValidationError, match="CLAMAV_HOST and CLAMAV_PORT"):
        _production_settings(CLAMAV_HOST="")


@pytest.mark.parametrize(
    ("setting", "value"),
    [("MAX_USER_STORAGE_MB", 0), ("MAX_USER_FILES", 0)],
)
def test_production_requires_positive_user_upload_quotas(setting, value):
    with pytest.raises(ValidationError, match="Per-user upload quotas"):
        _production_settings(**{setting: value})
