"""إضافة user_achievements (لوحة المتصدرين تُحسب مباشرة من بيانات موجودة، بدون جدول جديد)

Revision ID: 0012_gamification
Revises: 0011_assignments
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_gamification"
down_revision: Union[str, None] = "0011_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("achievement_key", sa.String(length=50), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "achievement_key", name="uq_user_achievement"),
    )


def downgrade() -> None:
    op.drop_table("user_achievements")
