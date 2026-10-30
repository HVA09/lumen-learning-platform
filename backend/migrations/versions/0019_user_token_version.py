"""Add a per-user token version for revocable sessions and LTI exchanges.

Revision ID: 0019_user_token_version
Revises: 0018_lti_one_time_auth
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_user_token_version"
down_revision: Union[str, None] = "0018_lti_one_time_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "lti_auth_codes",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("lti_auth_codes", "token_version")
    op.drop_column("users", "token_version")
