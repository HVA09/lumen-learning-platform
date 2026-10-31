import pytest
from cryptography.fernet import Fernet

from app.auth.totp_secrets import (
    TOTP_SECRET_PREFIX,
    TOTPSecretError,
    decrypt_totp_secret,
    encrypt_totp_secret,
    is_encrypted_totp_secret,
)
from app.config import settings


def test_totp_secret_round_trip_is_encrypted(monkeypatch):
    secret = "JBSWY3DPEHPK3PXP"
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())

    stored = encrypt_totp_secret(secret)

    assert stored.startswith(TOTP_SECRET_PREFIX)
    assert stored != secret
    assert secret not in stored
    assert is_encrypted_totp_secret(stored)
    assert decrypt_totp_secret(stored) == secret


def test_legacy_plaintext_secret_remains_readable(monkeypatch):
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", "")

    assert not is_encrypted_totp_secret("JBSWY3DPEHPK3PXP")
    assert decrypt_totp_secret("JBSWY3DPEHPK3PXP") == "JBSWY3DPEHPK3PXP"


def test_encryption_requires_a_configured_key(monkeypatch):
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", "")

    with pytest.raises(TOTPSecretError, match="not configured"):
        encrypt_totp_secret("JBSWY3DPEHPK3PXP")


def test_ciphertext_with_wrong_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    stored = encrypt_totp_secret("JBSWY3DPEHPK3PXP")

    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())
    with pytest.raises(TOTPSecretError, match="cannot be decrypted"):
        decrypt_totp_secret(stored)


def test_unknown_ciphertext_version_fails_closed():
    with pytest.raises(TOTPSecretError, match="unsupported encryption version"):
        decrypt_totp_secret("fernet:v2:anything")


def test_encrypted_marker_is_not_treated_as_plaintext_when_corrupted(monkeypatch):
    monkeypatch.setattr(settings, "TOTP_ENCRYPTION_KEY", Fernet.generate_key().decode())

    with pytest.raises(TOTPSecretError):
        decrypt_totp_secret(f"{TOTP_SECRET_PREFIX}not-a-valid-token")
