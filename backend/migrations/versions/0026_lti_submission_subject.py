"""Persist the exact external LTI subject through launch, session and submission.

Revision ID: 0026_lti_submission_subject
Revises: 0025_lti_ags_delivery_order
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_lti_submission_subject"
down_revision: Union[str, None] = "0025_lti_ags_delivery_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lti_auth_codes",
        sa.Column("lti_subject", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "auth_sessions",
        sa.Column("lti_subject", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "assignment_submissions",
        sa.Column("lti_subject", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assignment_submissions", "lti_subject")
    op.drop_column("auth_sessions", "lti_subject")
    op.drop_column("lti_auth_codes", "lti_subject")
