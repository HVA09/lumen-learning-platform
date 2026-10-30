"""
تهيئة أول مدير بطريقة تشغيلية آمنة — ليس مسار HTTP عامًا.

الاستخدام من مجلد backend بعد تسجيل الحساب وتأكيد بريده:
    python -m app.bootstrap_admin admin@example.com

يجب تشغيل هذا الأمر من بيئة موثوقة تملك صلاحية اتصال بقاعدة البيانات.
"""
import argparse
import sys

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole

ADMIN_BOOTSTRAP_LOCK_ID = 731904221


def promote_verified_account(db: Session, email: str) -> User:
    """Promote one verified account, refusing a second admin and serializing attempts."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email must not be empty.")

    db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": ADMIN_BOOTSTRAP_LOCK_ID},
    )

    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if user is None:
        raise ValueError("Account not found. Register the account first.")
    if not user.is_active:
        raise ValueError("Inactive accounts cannot be promoted.")
    if not user.is_email_verified:
        raise ValueError("Verify the account email before promoting it.")

    existing_admin = (
        db.query(User.id)
        .filter(User.role == UserRole.admin, User.id != user.id)
        .first()
    )
    if existing_admin:
        raise ValueError(
            "An administrator already exists; use the admin dashboard for later promotions."
        )

    user.role = UserRole.admin
    db.flush()
    return user


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a verified Lumen account to admin.")
    parser.add_argument("email", help="Email of the existing, verified account to promote")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        with db.begin():
            user = promote_verified_account(db, args.email)
        print(f"Granted admin role to verified account {user.email}.")
        return 0
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
