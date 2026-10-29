"""إضافة جدول review_cards (التكرار المتباعد SM-2+)

Revision ID: 0010_review_cards
Revises: 0009_lumen_curriculum
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0010_review_cards"
down_revision: Union[str, None] = "0009_lumen_curriculum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "review_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("front_text", sa.Text(), nullable=False),
        sa.Column("back_text", sa.Text(), nullable=False),
        sa.Column(
            "state",
            sa.Enum("new", "learning", "review", "relearning", name="cardstate"),
            nullable=False, server_default="new",
        ),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_leech", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("due_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_review_cards_user_due", "review_cards", ["user_id", "due_at"])


def downgrade() -> None:
    op.drop_table("review_cards")
    sa.Enum(name="cardstate").drop(op.get_bind(), checkfirst=True)
