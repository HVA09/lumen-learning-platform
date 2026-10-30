"""Password length policy for bcrypt's 72-byte input limit."""

MAX_BCRYPT_PASSWORD_BYTES = 72


def fits_bcrypt_password(password: str) -> bool:
    """Count UTF-8 bytes; short-circuit before encoding inputs longer than 72 chars."""
    if len(password) > MAX_BCRYPT_PASSWORD_BYTES:
        return False
    return len(password.encode("utf-8")) <= MAX_BCRYPT_PASSWORD_BYTES


def validate_bcrypt_password(password: str) -> str:
    """Reject values bcrypt would otherwise silently truncate."""
    if not fits_bcrypt_password(password):
        raise ValueError(
            f"Password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes when using bcrypt."
        )
    return password
