"""الفصول الدراسية + تحليل الأسئلة

- class_sections / class_enrollments: فصول يملكها معلّم، والطلاب ينضمون برمز دعوة
- assignments.class_section_id: نطاق اختياري للواجب (NULL = عام كما كان)
- question_results: صف لكل سؤال بكل محاولة مُسلَّمة (أساس تحليل الأسئلة للمعلّم)،
  ويُعبَّأ تلقائيًا من المحاولات المُسلَّمة سابقًا حتى لا تبدأ التحليلات من الصفر

Revision ID: 0016_classes_and_analytics
Revises: 0015_education_upgrade
Create Date: 2026-09-28

"""
import json
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0016_classes_and_analytics"
down_revision: Union[str, None] = "0015_education_upgrade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BACKFILL_BATCH_SIZE = 1000


def _backfill_question_results() -> None:
    """ينسخ نتائج الأسئلة من JSON المحاولات المُسلَّمة إلى الجدول الجديد (يتجاهل أسئلة صارت محذوفة)"""
    bind = op.get_bind()
    quiz_attempts = sa.table(
        "quiz_attempts",
        sa.column("id", sa.Integer),
        sa.column("results", sa.JSON),
        sa.column("submitted_at", sa.DateTime(timezone=True)),
    )
    questions = sa.table("questions", sa.column("id", sa.Integer))
    question_results = sa.table(
        "question_results",
        sa.column("quiz_attempt_id", sa.Integer),
        sa.column("question_id", sa.Integer),
        sa.column("correct", sa.Boolean),
        sa.column("given_answer", sa.JSON),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    valid_question_ids = {row.id for row in bind.execute(sa.select(questions.c.id))}
    batch: list[dict] = []

    def flush() -> None:
        if batch:
            bind.execute(question_results.insert(), batch)
            batch.clear()

    # نقرأ كل المحاولات أولًا ثم نُدخل — بدون تداخل بين قراءة نتيجة مفتوحة وتنفيذ إدخالات على نفس الاتصال
    attempts = bind.execute(
        sa.select(quiz_attempts.c.id, quiz_attempts.c.results, quiz_attempts.c.submitted_at).where(
            quiz_attempts.c.submitted_at.is_not(None)
        )
    ).fetchall()
    for attempt_id, results, submitted_at in attempts:
        if isinstance(results, str):
            try:
                results = json.loads(results)
            except ValueError:
                continue
        for item in results or []:
            if not isinstance(item, dict) or item.get("question_id") not in valid_question_ids:
                continue
            batch.append(
                {
                    "quiz_attempt_id": attempt_id,
                    "question_id": item["question_id"],
                    "correct": bool(item.get("correct")),
                    "given_answer": item.get("given_answer"),
                    "created_at": submitted_at,
                }
            )
            if len(batch) >= BACKFILL_BATCH_SIZE:
                flush()
    flush()


def upgrade() -> None:
    op.create_table(
        "class_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("teacher_user_id", sa.Integer(), nullable=False),
        sa.Column("invite_code", sa.String(length=8), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["teacher_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_class_sections_teacher_user_id", "class_sections", ["teacher_user_id"])
    op.create_index("ix_class_sections_invite_code", "class_sections", ["invite_code"], unique=True)

    op.create_table(
        "class_enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("class_section_id", sa.Integer(), nullable=False),
        sa.Column("student_user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["class_section_id"], ["class_sections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("class_section_id", "student_user_id", name="uq_enrollment_class_student"),
    )
    op.create_index("ix_class_enrollments_class_section_id", "class_enrollments", ["class_section_id"])
    op.create_index("ix_class_enrollments_student_user_id", "class_enrollments", ["student_user_id"])

    op.add_column("assignments", sa.Column("class_section_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_assignments_class_section", "assignments", "class_sections",
        ["class_section_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_assignments_class_section_id", "assignments", ["class_section_id"])

    op.create_table(
        "question_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_attempt_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("given_answer", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["quiz_attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_question_results_question_id", "question_results", ["question_id"])

    if not context.is_offline_mode():
        _backfill_question_results()


def downgrade() -> None:
    op.drop_table("question_results")

    op.drop_index("ix_assignments_class_section_id", table_name="assignments")
    op.drop_constraint("fk_assignments_class_section", "assignments", type_="foreignkey")
    op.drop_column("assignments", "class_section_id")

    op.drop_table("class_enrollments")
    op.drop_table("class_sections")
