"""Password size policy shared by HTTP schemas, hashing, and CLI tools."""

MAX_BCRYPT_PASSWORD_BYTES = 72


def fits_bcrypt_password(password: str) -> bool:
    """bcrypt uses a 72-byte input limit; count UTF-8 bytes, not characters."""
    return len(password.encode("utf-8")) <= MAX_BCRYPT_PASSWORD_BYTES


def validate_bcrypt_password(password: str) -> str:
    """Reject inputs bcrypt would otherwise truncate to the same hash."""
    if not fits_bcrypt_password(password):
        raise ValueError(
            f"Password must not exceed {MAX_BCRYPT_PASSWORD_BYTES} UTF-8 bytes when using bcrypt."
        )
    return password
