"""Serialize changes to Lumen's active administrator roster."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.user import User, UserRole

# Shared by application role changes, account deletion, and the authorized
# first-admin/recovery command. Keep this namespace stable across all callers.
ACTIVE_ADMIN_ROSTER_LOCK_NAMESPACE = 0x4C554D45  # "LUME"
ACTIVE_ADMIN_ROSTER_LOCK_ID = 0x41444D49  # "ADMI"


def lock_active_admin_ids(db: Session) -> set[int]:
    """Lock the roster and return IDs of active administrators.

    PostgreSQL's transaction-scoped advisory lock serializes all application
    paths that may remove or provision an active administrator. Row locks
    additionally protect the records participating in the decision. Other
    dialects retain the same decision logic for unit tests; PostgreSQL is the
    only supported production lock implementation.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:namespace, :lock_id)"),
            {
                "namespace": ACTIVE_ADMIN_ROSTER_LOCK_NAMESPACE,
                "lock_id": ACTIVE_ADMIN_ROSTER_LOCK_ID,
            },
        )

    rows = (
        db.query(User.id)
        .filter(User.role == UserRole.admin, User.is_active.is_(True))
        .with_for_update()
        .all()
    )
    return {row[0] for row in rows}
