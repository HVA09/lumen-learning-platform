"""Pydantic type for passwords stored with bcrypt."""

from typing import Annotated

from pydantic import AfterValidator, Field

from app.password_policy import MAX_BCRYPT_PASSWORD_BYTES, validate_bcrypt_password

# Limit character count before the byte validator; it avoids encoding arbitrarily
# large request strings while preserving the stricter UTF-8 byte constraint.
BcryptPassword = Annotated[
    str,
    Field(max_length=MAX_BCRYPT_PASSWORD_BYTES),
    AfterValidator(validate_bcrypt_password),
]
