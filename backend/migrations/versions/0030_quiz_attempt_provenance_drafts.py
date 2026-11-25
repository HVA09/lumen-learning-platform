"""Capture immutable quiz attempt provenance, question definitions, and draft answers.

Revision ID: 0030_quiz_attempt_provenance_drafts
Revises: 0029_lti_ags_manual_retry
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_quiz_attempt_provenance_drafts"
down_revision: Union[str, None] = "0029_lti_ags_manual_retry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quiz_attempts", sa.Column("class_section_id", sa.Integer(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("user_role_at_creation", sa.String(length=20), nullable=True))
    op.add_column("quiz_attempts", sa.Column("question_definition_snapshots", sa.JSON(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("draft_answers", sa.JSON(), nullable=True))
    op.add_column("quiz_attempts", sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_quiz_attempts_class_section_id",
        "quiz_attempts",
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
    op.create_index(
        "ix_question_results_definition_version",
        "question_results",
        ["question_id", "question_definition_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_question_results_definition_version", table_name="question_results")
    op.drop_column("question_results", "question_choices_snapshot")
    op.drop_column("question_results", "question_difficulty_snapshot")
    op.drop_column("question_results", "question_kind_snapshot")
    op.drop_column("question_results", "question_prompt_snapshot")
    op.drop_column("question_results", "question_definition_version")

    op.drop_index("ix_quiz_attempts_user_role_at_creation", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_class_section_id", table_name="quiz_attempts")
    op.drop_constraint("fk_quiz_attempts_class_section_id", "quiz_attempts", type_="foreignkey")
    op.drop_column("quiz_attempts", "expired_at")
    op.drop_column("quiz_attempts", "draft_answers")
    op.drop_column("quiz_attempts", "question_definition_snapshots")
    op.drop_column("quiz_attempts", "user_role_at_creation")
    op.drop_column("quiz_attempts", "class_section_id")
