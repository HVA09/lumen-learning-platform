"""Add LTI AGS resource mappings and durable grade passback outbox.

Revision ID: 0023_lti_ags_grade_passback
Revises: 0022_auth_sessions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0023_lti_ags_grade_passback"
down_revision: Union[str, None] = "0022_auth_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assignment_submissions",
        sa.Column("grade_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "lti_assignment_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("deployment_id", sa.String(length=255), nullable=False),
        sa.Column("resource_link_id", sa.String(length=255), nullable=False),
        sa.Column("lineitem_url", sa.String(length=2000), nullable=True),
        sa.Column("score_scope_allowed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("score_maximum", sa.Float(), server_default="100", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["platform_id"], ["lti_platforms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "platform_id", "deployment_id", "resource_link_id",
            name="uq_lti_assignment_link_resource",
        ),
        sa.CheckConstraint("score_maximum > 0", name="ck_lti_assignment_link_score_maximum"),
    )
    op.create_table(
        "lti_ags_grade_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_link_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("grade_version", sa.Integer(), nullable=False),
        sa.Column("lti_subject", sa.String(length=255), nullable=False),
        sa.Column("score_given", sa.Float(), nullable=False),
        sa.Column("score_maximum", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=255), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["assignment_link_id"], ["lti_assignment_links.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_id"], ["assignment_submissions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "assignment_link_id", "submission_id", "grade_version",
            name="uq_lti_ags_grade_event_version",
        ),
        sa.CheckConstraint(
            "score_given >= 0",
            name="ck_lti_ags_grade_event_score_nonnegative",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'dead')",
            name="ck_lti_ags_grade_event_status",
        ),
    )
    op.create_index(
        "ix_lti_ags_grade_events_due",
        "lti_ags_grade_events",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_lti_ags_grade_events_due", table_name="lti_ags_grade_events")
    op.drop_table("lti_ags_grade_events")
    op.drop_table("lti_assignment_links")
    op.drop_column("assignment_submissions", "grade_version")
