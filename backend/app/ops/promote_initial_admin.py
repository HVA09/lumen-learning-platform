"""Secure, one-time bootstrap for the first Lumen administrator.

Run only from an authorized interactive server/runtime shell after creating
and verifying the target account. There is intentionally no public API route.
"""
from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

# A namespaced, transaction-scoped PostgreSQL advisory lock. Both values fit
# signed int32 and are reserved for the Lumen first-admin bootstrap operation.
_ADMIN_BOOTSTRAP_LOCK_NAMESPACE = 0x4C554D45  # "LUME"
_ADMIN_BOOTSTRAP_LOCK_ID = 0x41444D49  # "ADMI"


def promote_initial_admin(db: Session, email: str, confirmation: str) -> None:
    """Promote one existing verified account if and only if no admin exists.

    The caller owns the transaction. The advisory lock serializes concurrent
    invocations; the target row is also locked before its role is changed.
    """
    normalized_email = email.strip().lower()
    if not normalized_email or confirmation.strip().lower() != normalized_email:
        raise ValueError("لم يتطابق تأكيد البريد الإلكتروني؛ لم يتم إجراء أي تغيير.")

    if db.get_bind().dialect.name != "postgresql":
        raise RuntimeError("أمر تهيئة المدير يتطلب PostgreSQL؛ لم يتم إجراء أي تغيير.")

    db.execute(
        text("SELECT pg_advisory_xact_lock(:namespace, :lock_id)"),
        {
            "namespace": _ADMIN_BOOTSTRAP_LOCK_NAMESPACE,
            "lock_id": _ADMIN_BOOTSTRAP_LOCK_ID,
        },
    )

    existing_admin = db.query(User.id).filter(User.role == UserRole.admin).first()
    if existing_admin is not None:
        raise ValueError("يوجد مدير بالفعل؛ لم يتم إجراء أي تغيير.")

    user = (
        db.query(User)
        .filter(User.email == normalized_email)
        .with_for_update()
        .first()
    )
    if user is None:
        raise ValueError("الحساب غير موجود؛ أنشئ الحساب أولاً ثم أكّد بريده.")
    if not user.is_active:
        raise ValueError("الحساب معطّل؛ لا يمكن ترقيته إلى مدير.")
    if not user.is_email_verified:
        raise ValueError("يجب تأكيد البريد الإلكتروني قبل منح صلاحية المدير.")

    user.role = UserRole.admin
    db.add(
        AuditLog(
            user_id=user.id,
            event_type="first_admin_bootstrap",
            description="First administrator provisioned through the authorized server-side bootstrap command.",
        )
    )
    db.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Securely provision the first Lumen administrator."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address of the existing, active, verified account",
    )
    args = parser.parse_args(argv)

    if not sys.stdin.isatty():
        print(
            "يلزم تشغيل هذا الأمر من طرفية تفاعلية؛ لم يتم إجراء أي تغيير.",
            file=sys.stderr,
        )
        return 2

    try:
        confirmation = input(
            f"سيتم منح صلاحية المدير للحساب {args.email}. اكتب البريد نفسه للتأكيد: "
        )
        with SessionLocal() as db:
            with db.begin():
                promote_initial_admin(db, args.email, confirmation)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("تم إلغاء العملية؛ لم يتم إجراء أي تغيير.", file=sys.stderr)
        return 2
    except Exception:
        # Avoid printing SQL/connection details or credentials to the terminal.
        logger.exception("First administrator bootstrap failed.")
        print(
            "تعذر إكمال تهيئة المدير. راجع سجل الخادم المصرح به؛ لم تُعرض تفاصيل الاتصال.",
            file=sys.stderr,
        )
        return 1

    print(f"تمت ترقية {args.email.strip().lower()} إلى admin بنجاح.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
