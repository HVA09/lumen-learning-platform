"""Persist per-attempt AGS timestamps and superseded event state.

Revision ID: 0025_lti_ags_delivery_order
Revises: 0024_lti_resource_discovery
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_lti_ags_delivery_order"
down_revision: Union[str, None] = "0024_lti_resource_discovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lti_ags_grade_events",
        sa.Column("score_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE lti_ags_grade_events "
        "SET score_timestamp = created_at "
        "WHERE score_timestamp IS NULL"
    )
    op.alter_column(
        "lti_ags_grade_events",
        "score_timestamp",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.drop_constraint(
        "ck_lti_ags_grade_event_status",
        "lti_ags_grade_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_lti_ags_grade_event_status",
        "lti_ags_grade_events",
        "status IN ('pending', 'sent', 'dead', 'superseded')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE lti_ags_grade_events SET status = 'dead' WHERE status = 'superseded'"
    )
    op.drop_constraint(
        "ck_lti_ags_grade_event_status",
        "lti_ags_grade_events",
        type_="check",
    )
    op.create_check_constraint(
        "ck_lti_ags_grade_event_status",
        "lti_ags_grade_events",
        "status IN ('pending', 'sent', 'dead')",
    )
    op.drop_column("lti_ags_grade_events", "score_timestamp")
