"""Encryption helpers for TOTP shared secrets stored on user records."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

TOTP_SECRET_PREFIX = "fernet:v1:"


class TOTPSecretError(RuntimeError):
    """Raised when a stored TOTP secret cannot be safely encrypted or decrypted."""


def _fernet() -> Fernet:
    key = settings.TOTP_ENCRYPTION_KEY.strip()
    if not key:
        raise TOTPSecretError("TOTP_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (UnicodeEncodeError, ValueError, TypeError) as exc:
        raise TOTPSecretError("TOTP_ENCRYPTION_KEY is invalid") from exc


def is_encrypted_totp_secret(value: str | None) -> bool:
    return bool(value and value.startswith(TOTP_SECRET_PREFIX))


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt a plaintext TOTP secret; never persist plaintext through this helper."""
    if not secret:
        raise TOTPSecretError("TOTP secret cannot be empty")
    token = _fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{TOTP_SECRET_PREFIX}{token}"


def decrypt_totp_secret(stored_value: str) -> str:
    """Read v1 ciphertext or a legacy plaintext value pending successful-login migration."""
    if not stored_value:
        raise TOTPSecretError("TOTP secret is empty")

    if stored_value.startswith(TOTP_SECRET_PREFIX):
        try:
            token = stored_value[len(TOTP_SECRET_PREFIX) :].encode("ascii")
            return _fernet().decrypt(token).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as exc:
            raise TOTPSecretError("Stored TOTP secret cannot be decrypted") from exc

    # Reserve the namespace for versioned ciphertext. Unknown versions must fail closed
    # rather than being mistaken for legacy plaintext.
    if stored_value.startswith("fernet:"):
        raise TOTPSecretError("Stored TOTP secret uses an unsupported encryption version")

    # Existing accounts created before this change stored base32 TOTP values in plaintext.
    return stored_value
