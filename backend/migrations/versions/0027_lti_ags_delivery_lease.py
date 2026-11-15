"""Add durable per-learner AGS delivery leases.

Revision ID: 0027_lti_ags_delivery_lease
Revises: 0026_lti_submission_subject
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027_lti_ags_delivery_lease"
down_revision: Union[str, None] = "0026_lti_submission_subject"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lti_ags_delivery_leases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_link_id", sa.Integer(), nullable=False),
        sa.Column("subject_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_token", sa.String(length=32), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_link_id"],
            ["lti_assignment_links.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["lti_ags_grade_events.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "assignment_link_id",
            "subject_hash",
            name="uq_lti_ags_delivery_lease_subject",
        ),
    )
    op.create_index(
        "ix_lti_ags_delivery_leases_locked_until",
        "lti_ags_delivery_leases",
        ["locked_until"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lti_ags_delivery_leases_locked_until",
        table_name="lti_ags_delivery_leases",
    )
    op.drop_table("lti_ags_delivery_leases")
