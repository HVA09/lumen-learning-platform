"""Persist verified LTI launch context and exact submission target.

Revision ID: 0024_lti_resource_discovery
Revises: 0023_lti_ags_grade_passback
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_lti_resource_discovery"
down_revision: Union[str, None] = "0023_lti_ags_grade_passback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("lti_auth_codes", sa.Column("lti_platform_id", sa.Integer(), nullable=True))
    op.add_column("lti_auth_codes", sa.Column("lti_deployment_id", sa.String(length=255), nullable=True))
    op.add_column("lti_auth_codes", sa.Column("lti_resource_link_id", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_lti_auth_codes_platform", "lti_auth_codes", "lti_platforms",
        ["lti_platform_id"], ["id"], ondelete="SET NULL",
    )

    op.add_column("auth_sessions", sa.Column("lti_platform_id", sa.Integer(), nullable=True))
    op.add_column("auth_sessions", sa.Column("lti_deployment_id", sa.String(length=255), nullable=True))
    op.add_column("auth_sessions", sa.Column("lti_resource_link_id", sa.String(length=255), nullable=True))
    op.create_foreign_key(
        "fk_auth_sessions_lti_platform", "auth_sessions", "lti_platforms",
        ["lti_platform_id"], ["id"], ondelete="SET NULL",
    )

    op.add_column("assignment_submissions", sa.Column("lti_assignment_link_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_assignment_submissions_lti_assignment_link",
        "assignment_submissions", "lti_assignment_links",
        ["lti_assignment_link_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "ix_assignment_submissions_lti_assignment_link_id",
        "assignment_submissions", ["lti_assignment_link_id"],
    )

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
        "lti_resource_link_discoveries", ["last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lti_resource_link_discoveries_seen", table_name="lti_resource_link_discoveries")
    op.drop_table("lti_resource_link_discoveries")
    op.drop_index("ix_assignment_submissions_lti_assignment_link_id", table_name="assignment_submissions")
    op.drop_constraint("fk_assignment_submissions_lti_assignment_link", "assignment_submissions", type_="foreignkey")
    op.drop_column("assignment_submissions", "lti_assignment_link_id")
    op.drop_constraint("fk_auth_sessions_lti_platform", "auth_sessions", type_="foreignkey")
    op.drop_column("auth_sessions", "lti_resource_link_id")
    op.drop_column("auth_sessions", "lti_deployment_id")
    op.drop_column("auth_sessions", "lti_platform_id")
    op.drop_constraint("fk_lti_auth_codes_platform", "lti_auth_codes", type_="foreignkey")
    op.drop_column("lti_auth_codes", "lti_resource_link_id")
    op.drop_column("lti_auth_codes", "lti_deployment_id")
    op.drop_column("lti_auth_codes", "lti_platform_id")
