"""إضافة جداول LTI 1.3: المنصات المسجّلة وربط المستخدمين

Revision ID: 0014_lti
Revises: 0013_programming_subject
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014_lti"
down_revision: Union[str, None] = "0013_programming_subject"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lti_platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("issuer", sa.String(length=500), nullable=False),
        sa.Column("client_id", sa.String(length=255), nullable=False),
        sa.Column("deployment_id", sa.String(length=255), nullable=False),
        sa.Column("auth_login_url", sa.String(length=500), nullable=False),
        sa.Column("auth_token_url", sa.String(length=500), nullable=False),
        sa.Column("jwks_url", sa.String(length=500), nullable=False),
        sa.UniqueConstraint("issuer", "client_id", name="uq_lti_platform_issuer_client"),
    )

    op.create_table(
        "lti_user_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("lti_subject", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["platform_id"], ["lti_platforms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("platform_id", "lti_subject", name="uq_lti_user_link"),
    )


def downgrade() -> None:
    op.drop_table("lti_user_links")
    op.drop_table("lti_platforms")
