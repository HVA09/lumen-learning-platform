"""Persist payment webhook IDs to prevent repeated processing.

Revision ID: 0021_webhook_idempotency
Revises: 0020_totp_secret_ciphertext
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_webhook_idempotency"
down_revision: Union[str, None] = "0020_totp_secret_ciphertext"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('stripe', 'paypal')",
            name="ck_processed_webhook_provider",
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_processed_webhook_provider_event",
        ),
    )
    op.create_index(
        "ix_processed_webhook_received_at",
        "processed_webhook_events",
        ["received_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_processed_webhook_received_at",
        table_name="processed_webhook_events",
    )
    op.drop_table("processed_webhook_events")
