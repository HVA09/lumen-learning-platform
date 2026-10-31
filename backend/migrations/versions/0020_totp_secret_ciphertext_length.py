"""Widen the TOTP secret column to hold authenticated ciphertext.

Revision ID: 0020_totp_secret_ciphertext_length
Revises: 0019_user_token_version
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_totp_secret_ciphertext"
down_revision: Union[str, None] = "0019_user_token_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fernet ciphertext is longer than the original 64-character base32 plaintext.
    # Keep old values intact; application code migrates them lazily after valid TOTP use.
    op.alter_column(
        "users",
        "totp_secret",
        existing_type=sa.String(length=64),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Intentionally retain VARCHAR(255). Encrypted values can exceed 64 characters,
    # and narrowing this column could fail or destroy authentication data.
    pass
