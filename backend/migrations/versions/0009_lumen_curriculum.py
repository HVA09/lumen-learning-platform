"""إضافة طبقة المنهج: subjects, topics, topic_mastery + بيانات أولية

Revision ID: 0009_lumen_curriculum
Revises: 0008_notifications
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_lumen_curriculum"
down_revision: Union[str, None] = "0008_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("name_ar", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False, unique=True),
        sa.Column("name_ar", sa.String(length=255), nullable=False),
        sa.Column("name_en", sa.String(length=255), nullable=False),
        sa.Column("learning_outcomes_ar", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("skill_tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("prerequisite_topic_id", sa.Integer(), nullable=True),
        sa.Column("simulation_type", sa.String(length=50), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerequisite_topic_id"], ["topics.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "topic_mastery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("mastery_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gateway_quiz_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "topic_id", name="uq_topic_mastery_user_topic"),
    )
    op.create_index("ix_topic_mastery_user_id", "topic_mastery", ["user_id"])

    # بيانات أولية: مادتان (رياضيات وفيزياء) بمواضيع أساسية — عدّلها/أضف عليها من لوحة الإدارة لاحقًا
    subjects_table = sa.table(
        "subjects", sa.column("id", sa.Integer), sa.column("slug", sa.String),
        sa.column("name_ar", sa.String), sa.column("name_en", sa.String), sa.column("order_index", sa.Integer),
    )
    op.bulk_insert(subjects_table, [
        {"id": 1, "slug": "math", "name_ar": "الرياضيات", "name_en": "Mathematics", "order_index": 1},
        {"id": 2, "slug": "physics", "name_ar": "الفيزياء", "name_en": "Physics", "order_index": 2},
    ])

    topics_table = sa.table(
        "topics", sa.column("id", sa.Integer), sa.column("subject_id", sa.Integer), sa.column("slug", sa.String),
        sa.column("name_ar", sa.String), sa.column("name_en", sa.String),
        sa.column("learning_outcomes_ar", sa.JSON), sa.column("skill_tags", sa.JSON),
        sa.column("prerequisite_topic_id", sa.Integer), sa.column("simulation_type", sa.String),
        sa.column("order_index", sa.Integer),
    )
    op.bulk_insert(topics_table, [
        {
            "id": 1, "subject_id": 1, "slug": "linear-equations", "name_ar": "المعادلات الخطية", "name_en": "Linear Equations",
            "learning_outcomes_ar": ["يحل معادلة خطية بمتغيّر واحد", "يمثّل معادلة خطية بيانيًا"],
            "skill_tags": ["algebra", "linear-functions"], "prerequisite_topic_id": None,
            "simulation_type": "linear-function", "order_index": 1,
        },
        {
            "id": 2, "subject_id": 1, "slug": "derivatives-intro", "name_ar": "مقدمة في المشتقات", "name_en": "Intro to Derivatives",
            "learning_outcomes_ar": ["يشرح مفهوم معدل التغيّر اللحظي", "يحسب مشتقة دالة كثيرة حدود بسيطة"],
            "skill_tags": ["calculus"], "prerequisite_topic_id": 1,
            "simulation_type": "derivative", "order_index": 2,
        },
        {
            "id": 3, "subject_id": 2, "slug": "projectile-motion", "name_ar": "الحركة المقذوفة", "name_en": "Projectile Motion",
            "learning_outcomes_ar": ["يحلل حركة جسم مقذوف لمركبتين", "يحسب المدى الأفقي والزمن"],
            "skill_tags": ["kinematics", "vectors"], "prerequisite_topic_id": None,
            "simulation_type": "projectile", "order_index": 1,
        },
        {
            "id": 4, "subject_id": 2, "slug": "dc-circuits", "name_ar": "الدوائر الكهربائية (تيار مستمر)", "name_en": "DC Circuits",
            "learning_outcomes_ar": ["يطبّق قانون أوم", "يحسب المقاومة المكافئة بدائرة توالي/توازي"],
            "skill_tags": ["electricity"], "prerequisite_topic_id": None,
            "simulation_type": "circuits-dc", "order_index": 2,
        },
    ])


def downgrade() -> None:
    op.drop_table("topic_mastery")
    op.drop_table("topics")
    op.drop_table("subjects")
