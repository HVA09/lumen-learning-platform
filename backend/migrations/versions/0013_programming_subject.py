"""إضافة مادة البرمجة مع موضوع يربط بمختبر بايثون (Pyodide)

Revision ID: 0013_programming_subject
Revises: 0012_gamification
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_programming_subject"
down_revision: Union[str, None] = "0012_gamification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    subjects_table = sa.table(
        "subjects", sa.column("id", sa.Integer), sa.column("slug", sa.String),
        sa.column("name_ar", sa.String), sa.column("name_en", sa.String), sa.column("order_index", sa.Integer),
    )
    op.bulk_insert(subjects_table, [
        {"id": 3, "slug": "programming", "name_ar": "البرمجة", "name_en": "Programming", "order_index": 3},
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
            "id": 5, "subject_id": 3, "slug": "python-loops", "name_ar": "الحلقات التكرارية بلغة بايثون",
            "name_en": "Python Loops",
            "learning_outcomes_ar": ["يكتب حلقة for بلغة بايثون", "يستخدم المتغيرات لتجميع نتيجة داخل حلقة"],
            "skill_tags": ["programming", "python"], "prerequisite_topic_id": None,
            "simulation_type": "python-lab", "order_index": 1,
        },
    ])


def downgrade() -> None:
    op.execute("DELETE FROM topics WHERE id = 5")
    op.execute("DELETE FROM subjects WHERE id = 3")
