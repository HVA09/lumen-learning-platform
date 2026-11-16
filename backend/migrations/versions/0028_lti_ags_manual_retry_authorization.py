"""Add one-shot admin authorization for retrying exhausted AGS grade events.

Revision ID: 0028_lti_ags_manual_retry_authorization
Revises: 0027_lti_ags_delivery_lease
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_lti_ags_manual_retry"
down_revision: Union[str, None] = "0027_lti_ags_delivery_lease"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lti_ags_grade_events",
        sa.Column("manual_retry_requested_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lti_ags_grade_events", "manual_retry_requested_at")
