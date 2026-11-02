"""Pydantic type for passwords stored with bcrypt."""

from typing import Annotated

from pydantic import AfterValidator, Field

from app.password_policy import validate_bcrypt_password

# Apply a character cap before UTF-8 byte validation to bound request processing.
# The validator still enforces the stricter 72-byte limit for non-ASCII passwords.
BcryptPassword = Annotated[
    str,
    Field(max_length=72),
    AfterValidator(validate_bcrypt_password),
]
