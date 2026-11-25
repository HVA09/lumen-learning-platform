"""Capture immutable quiz attempt provenance, question definitions, and draft answers.

Revision ID: 0030_quiz_drafts
Revises: 0029_lti_ags_manual_retry
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_quiz_drafts"
down_revision: Union[str, None] = "0029_lti_ags_manual_retry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quiz_attempts", sa.Column("class_section_id", sa.Integer(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("user_role_at_creation", sa.String(length=20), nullable=True))
    op.add_column("quiz_attempts", sa.Column("question_definition_snapshots", sa.JSON(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("draft_answers", sa.JSON(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True))
    # Batch mode preserves SQLite compatibility while emitting a normal FK on PostgreSQL.
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.create_foreign_key(
            "fk_quiz_attempts_class_section_id",
            "class_sections",
            ["class_section_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index("ix_quiz_attempts_class_section_id", "quiz_attempts", ["class_section_id"])
    op.create_index("ix_quiz_attempts_user_role_at_creation", "quiz_attempts", ["user_role_at_creation"])

    op.add_column("question_results", sa.Column("question_definition_version", sa.String(length=64), nullable=True))
    op.add_column("question_results", sa.Column("question_prompt_snapshot", sa.Text(), nullable=True))
    op.add_column("question_results", sa.Column("question_kind_snapshot", sa.String(length=20), nullable=True))
    op.add_column("question_results", sa.Column("question_difficulty_snapshot", sa.Integer(), nullable=True))
    op.add_column("question_results", sa.Column("question_choices_snapshot", sa.JSON(), nullable=True))
    op.add_column("question_results", sa.Column("question_correct_answer_snapshot", sa.JSON(), nullable=True))
    op.add_column("question_results", sa.Column("question_tolerance_snapshot", sa.Float(), nullable=True))
    op.create_index(
        "ix_question_results_definition_version",
        "question_results",
        ["question_id", "question_definition_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_results_definition_version", table_name="question_results")
    with op.batch_alter_table("question_results") as batch_op:
        batch_op.drop_column("question_tolerance_snapshot")
        batch_op.drop_column("question_correct_answer_snapshot")
        batch_op.drop_column("question_choices_snapshot")
        batch_op.drop_column("question_difficulty_snapshot")
        batch_op.drop_column("question_kind_snapshot")
        batch_op.drop_column("question_prompt_snapshot")
        batch_op.drop_column("question_definition_version")

    op.drop_index("ix_quiz_attempts_user_role_at_creation", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_class_section_id", table_name="quiz_attempts")
    with op.batch_alter_table("quiz_attempts") as batch_op:
        batch_op.drop_constraint("fk_quiz_attempts_class_section_id", type_="foreignkey")
        batch_op.drop_column("expired_at")
        batch_op.drop_column("draft_answers")
        batch_op.drop_column("question_definition_snapshots")
        batch_op.drop_column("user_role_at_creation")
        batch_op.drop_column("class_section_id")
