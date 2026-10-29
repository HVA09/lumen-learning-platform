"""إزالة الذكاء الاصطناعي + ترقية النظام التعليمي

ماذا يسوي هذا الـ migration:
- يحذف جداول المحادثات والرسائل وسجل استخدام AI (تحذير: يحذف سجل المحادثات نهائيًا —
  خذ نسخة احتياطية قبل الترقية لو تحتاجه)
- يشيل حد طلبات AI اليومي من خطط الاشتراك
- الواجبات صارت بتقييم المعلّم اليدوي: إعادة تسمية عمودي التقييم، حذف الأعمدة اللي كانت
  ترسلها الواجهة بدون تحقق (simulation_*)، وإضافة is_late وgraded_by_user_id
- دور جديد للمستخدم: teacher
- جداول جديدة: lessons, lesson_progress, questions, quiz_attempts, topic_cards, study_days
- يزرع الدروس والأسئلة وبطاقات المراجعة الجاهزة (idempotent — راجع app/content/seeder.py)

Revision ID: 0015_education_upgrade
Revises: 0014_lti
Create Date: 2026-09-21

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa

revision: str = "0015_education_upgrade"
down_revision: Union[str, None] = "0014_lti"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
    )


def upgrade() -> None:
    bind = op.get_bind()

    # ---- 1) دور المعلّم (أول خطوة: ALTER TYPE ... ADD VALUE يحتاج التنفيذ خارج transaction) ----
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'teacher'")

    # ---- 2) إزالة الذكاء الاصطناعي ----
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("usage_logs")
    sa.Enum(name="messagerole").drop(bind, checkfirst=True)
    op.drop_column("plans", "daily_ai_request_limit")

    # ---- 3) الواجبات: تقييم يدوي من المعلّم ----
    op.alter_column("assignment_submissions", "ai_grade_percentage", new_column_name="grade_percentage")
    op.alter_column("assignment_submissions", "ai_feedback", new_column_name="feedback")
    op.add_column(
        "assignment_submissions",
        sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "assignment_submissions", sa.Column("graded_by_user_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_submission_graded_by", "assignment_submissions", "users",
        ["graded_by_user_id"], ["id"], ondelete="SET NULL",
    )
    op.drop_column("assignment_submissions", "simulation_achieved_value")
    op.drop_column("assignment_submissions", "simulation_passed")
    # تسليمات صُنّفت "graded" بدون نسبة (كان التقييم الآلي فاشل) ترجع بانتظار تقييم المعلّم
    op.execute(
        "UPDATE assignment_submissions SET status = 'submitted', feedback = NULL, graded_at = NULL "
        "WHERE status = 'graded' AND grade_percentage IS NULL"
    )

    # ---- 4) جداول المحتوى والتقييم ----
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title_ar", sa.String(length=255), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        _created_at(),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("topic_id", "slug", name="uq_lesson_topic_slug"),
    )
    op.create_index("ix_lessons_topic_id", "lessons", ["topic_id"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("lesson_id", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )
    op.create_index("ix_lesson_progress_user_id", "lesson_progress", ["user_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("prompt_ar", sa.Text(), nullable=False),
        sa.Column("choices", sa.JSON(), nullable=True),
        sa.Column("correct_answer", sa.JSON(), nullable=False),
        sa.Column("tolerance", sa.Float(), nullable=True),
        sa.Column("explanation_ar", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("key", name="uq_questions_key"),
    )
    op.create_index("ix_questions_topic_id", "questions", ["topic_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("question_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("results", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("score_percentage", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        _created_at(),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_quiz_attempts_user_topic", "quiz_attempts", ["user_id", "topic_id"])

    op.create_table(
        "topic_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=True),
        sa.Column("front_text", sa.Text(), nullable=False),
        sa.Column("back_text", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key", name="uq_topic_cards_key"),
    )
    op.create_index("ix_topic_cards_topic_id", "topic_cards", ["topic_id"])

    op.create_table(
        "study_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "day", name="uq_study_day_user_day"),
    )
    op.create_index("ix_study_days_user_id", "study_days", ["user_id"])

    # ---- 5) المحتوى الأولي (لا يُنفَّذ بوضع --sql لأنه يحتاج قراءة من قاعدة البيانات) ----
    if not context.is_offline_mode():
        from app.content.seeder import seed_all

        seed_all(bind)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("study_days")
    op.drop_table("topic_cards")
    op.drop_table("quiz_attempts")
    op.drop_table("questions")
    op.drop_table("lesson_progress")
    op.drop_table("lessons")

    op.add_column("assignment_submissions", sa.Column("simulation_passed", sa.Boolean(), nullable=True))
    op.add_column(
        "assignment_submissions", sa.Column("simulation_achieved_value", sa.Float(), nullable=True)
    )
    op.drop_constraint("fk_submission_graded_by", "assignment_submissions", type_="foreignkey")
    op.drop_column("assignment_submissions", "graded_by_user_id")
    op.drop_column("assignment_submissions", "is_late")
    op.alter_column("assignment_submissions", "feedback", new_column_name="ai_feedback")
    op.alter_column("assignment_submissions", "grade_percentage", new_column_name="ai_grade_percentage")

    op.add_column(
        "plans",
        sa.Column("daily_ai_request_limit", sa.Integer(), nullable=False, server_default="20"),
    )
    op.execute("UPDATE plans SET daily_ai_request_limit = 500 WHERE name = 'Pro'")

    # بنية جداول الذكاء الاصطناعي فقط (البيانات المحذوفة ما ترجع)
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_conversations_user_id_created_at", "conversations", ["user_id", "created_at"]
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Enum("user", "assistant", name="messagerole"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=100), nullable=False),
        _created_at(),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_usage_logs_user_id_created_at", "usage_logs", ["user_id", "created_at"])

    # PostgreSQL ما يسمح بحذف قيمة من enum — نترك 'teacher' بالنوع ونحوّل المعلّمين لطلاب
    op.execute("UPDATE users SET role = 'user' WHERE role = 'teacher'")
