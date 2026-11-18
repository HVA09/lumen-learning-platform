"""Add lesson ownership for shared curriculum governance.

Revision ID: 0023_content_ownership
Revises: 0022_auth_sessions
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_content_ownership"
down_revision: Union[str, None] = "0022_auth_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_lessons_created_by_user_id", "lessons", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_lessons_created_by_user_id", table_name="lessons")
    op.drop_column("lessons", "created_by_user_id")
