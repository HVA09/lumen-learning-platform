"""Discover LTI resource links before an administrator maps them to assignments.

Revision ID: 0024_lti_resource_discovery
Revises: 0023_lti_ags_grade_passback
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024_lti_resource_discovery"
down_revision: Union[str, None] = "0023_lti_ags_grade_passback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lti_resource_link_discoveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("deployment_id", sa.String(length=255), nullable=False),
        sa.Column("resource_link_id", sa.String(length=255), nullable=False),
        sa.Column("lineitem_url", sa.String(length=2000), nullable=True),
        sa.Column("score_scope_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["platform_id"], ["lti_platforms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "platform_id", "deployment_id", "resource_link_id",
            name="uq_lti_resource_link_discovery",
        ),
    )
    op.create_index(
        "ix_lti_resource_link_discoveries_seen",
        "lti_resource_link_discoveries",
        ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lti_resource_link_discoveries_seen",
        table_name="lti_resource_link_discoveries",
    )
    op.drop_table("lti_resource_link_discoveries")
