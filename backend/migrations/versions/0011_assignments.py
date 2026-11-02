"""إضافة الواجبات وتسليماتها

Revision ID: 0011_assignments
Revises: 0010_review_cards
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_assignments"
down_revision: Union[str, None] = "0010_review_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rubric_criteria", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "assignment_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("student_user_id", sa.Integer(), nullable=False),
        sa.Column("written_answer", sa.Text(), nullable=True),
        sa.Column("simulation_achieved_value", sa.Float(), nullable=True),
        sa.Column("simulation_passed", sa.Boolean(), nullable=True),
        sa.Column("ai_grade_percentage", sa.Float(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.Enum("pending", "submitted", "graded", name="submissionstatus"),
            nullable=False, server_default="pending",
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("assignment_id", "student_user_id", name="uq_submission_assignment_student"),
    )


def downgrade() -> None:
    op.drop_table("assignment_submissions")
    op.drop_table("assignments")
    sa.Enum(name="submissionstatus").drop(op.get_bind(), checkfirst=True)
