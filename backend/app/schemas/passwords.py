"""Pydantic type for passwords stored with bcrypt."""

from typing import Annotated

from pydantic import AfterValidator

from app.password_policy import validate_bcrypt_password

BcryptPassword = Annotated[str, AfterValidator(validate_bcrypt_password)]
