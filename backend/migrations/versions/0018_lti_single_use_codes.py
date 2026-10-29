"""Add one-time LTI login states and exchange codes.

Revision ID: 0018_lti_single_use_codes
Revises: 0017_latex_content
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_lti_single_use_codes"
down_revision: Union[str, None] = "0017_latex_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lti_login_states",
        sa.Column("state_hash", sa.String(length=64), primary_key=True),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("target_link_uri", sa.String(length=1000), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["platform_id"], ["lti_platforms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lti_login_states_expires_at", "lti_login_states", ["expires_at"])

    op.create_table(
        "lti_auth_codes",
        sa.Column("code_hash", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lti_auth_codes_expires_at", "lti_auth_codes", ["expires_at"])
    op.create_index("ix_lti_auth_codes_user_id", "lti_auth_codes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_lti_auth_codes_user_id", table_name="lti_auth_codes")
    op.drop_index("ix_lti_auth_codes_expires_at", table_name="lti_auth_codes")
    op.drop_table("lti_auth_codes")
    op.drop_index("ix_lti_login_states_expires_at", table_name="lti_login_states")
    op.drop_table("lti_login_states")
