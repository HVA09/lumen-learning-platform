"""Secure bootstrap and recovery for a Lumen administrator.

Run only from an authorized interactive server/runtime shell after creating
and verifying the target account. There is intentionally no public API route.
"""
from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.admin_guard import lock_active_admin_ids
from app.config import settings
from app.database import SessionLocal, engine
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


def _build_confirmation_phrase(email: str, environment: str, database_url: URL) -> str:
    """Identify the target without exposing DB username, password, or query."""
    host = database_url.host or "<no-host>"
    port = str(database_url.port) if database_url.port is not None else "<default-port>"
    database = database_url.database or "<no-database>"
    target_environment = environment.strip() or "<unspecified>"
    return f"{email.strip()} | {target_environment} | {host}:{port}/{database}"


def promote_initial_admin(db: Session, email: str, confirmation: str) -> None:
    """Promote one existing verified account if and only if no active admin exists.

    The caller owns the transaction. The advisory lock serializes concurrent
    invocations; the target row is also locked before its role is changed.
    """
    normalized_email = email.strip()
    if not normalized_email or confirmation.strip() != normalized_email:
        raise ValueError("لم يتطابق تأكيد البريد الإلكتروني؛ لم يتم إجراء أي تغيير.")

    if db.get_bind().dialect.name != "postgresql":
        raise RuntimeError("أمر تهيئة المدير يتطلب PostgreSQL؛ لم يتم إجراء أي تغيير.")

    # The same transaction-scoped lock protects bootstrap/recovery and every
    # application path that can remove an active administrator.
    active_admin_ids = lock_active_admin_ids(db)
    if active_admin_ids:
        raise ValueError("يوجد مدير نشط بالفعل؛ لم يتم إجراء أي تغيير.")

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
            description="Administrator provisioned through the authorized server-side bootstrap/recovery command.",
        )
    )
    db.flush()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Securely provision or recover a Lumen administrator when none is active."
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
        phrase = _build_confirmation_phrase(args.email, settings.ENVIRONMENT, engine.url)
        print(
            "قاعدة الهدف (من دون بيانات اعتماد): "
            f"environment={settings.ENVIRONMENT}, "
            f"host={engine.url.host or '<no-host>'}, "
            f"port={engine.url.port if engine.url.port is not None else '<default-port>'}, "
            f"database={engine.url.database or '<no-database>'}"
        )
        confirmation = input(
            "اكتب عبارة التأكيد التالية حرفيًا للمتابعة: " + phrase + "\n> "
        )
        if confirmation != phrase:
            raise ValueError("لم تتطابق عبارة التأكيد؛ لم يتم إجراء أي تغيير.")
        with SessionLocal() as db:
            with db.begin():
                promote_initial_admin(db, args.email, args.email)
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

    print(f"تمت ترقية {args.email.strip()} إلى admin بنجاح.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
