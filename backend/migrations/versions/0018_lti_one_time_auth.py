"""Store single-use LTI OIDC state and short-lived exchange codes.

Revision ID: 0018_lti_one_time_auth
Revises: 0017_latex_content
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_lti_one_time_auth"
down_revision: Union[str, None] = "0017_latex_content"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lti_auth_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("target_link_uri", sa.String(length=1000), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["platform_id"], ["lti_platforms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("state_hash", name="uq_lti_auth_states_state_hash"),
    )
    op.create_table(
        "lti_auth_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("code_hash", name="uq_lti_auth_codes_code_hash"),
    )


def downgrade() -> None:
    op.drop_table("lti_auth_codes")
    op.drop_table("lti_auth_states")
