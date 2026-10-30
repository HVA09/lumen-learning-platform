"""
تهيئة أول مدير بطريقة تشغيلية آمنة — ليس مسار HTTP عامًا.

الاستخدام من مجلد backend بعد تسجيل الحساب وتأكيد بريده:
    python -m app.bootstrap_admin admin@example.com

يجب تشغيل هذا الأمر من بيئة موثوقة تملك صلاحية اتصال بقاعدة البيانات.
"""
import argparse
import sys

from sqlalchemy import func, text

from app.database import SessionLocal
from app.models.user import User, UserRole

ADMIN_BOOTSTRAP_LOCK_ID = 731904221


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a verified Lumen account to admin.")
    parser.add_argument("email", help="Email of the existing, verified account to promote")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if not email:
        parser.error("email must not be empty")

    db = SessionLocal()
    try:
        with db.begin():
            # Serialize concurrent bootstrap invocations at the database level.
            db.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": ADMIN_BOOTSTRAP_LOCK_ID},
            )
            user = db.query(User).filter(func.lower(User.email) == email).first()
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

        print(f"Granted admin role to verified account {email}.")
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
