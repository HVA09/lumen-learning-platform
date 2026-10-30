"""Add per-user token version for revocable sessions and one-time password resets.

Revision ID: 0019_user_token_version
Revises: 0018_lti_single_use_codes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0019_user_token_version"
down_revision: Union[str, None] = "0018_lti_single_use_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lti_auth_codes",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
    op.drop_column("lti_auth_codes", "token_version")
