"""
تهيئة أول مدير بطريقة تشغيلية آمنة — ليس مسار HTTP عامًا.

الاستخدام من مجلد backend بعد تسجيل الحساب وتأكيد بريده:
    python -m app.bootstrap_admin admin@example.com

يجب تشغيل هذا الأمر من بيئة موثوقة تملك صلاحية اتصال بقاعدة البيانات.
"""
import argparse
import sys

from sqlalchemy import func

from app.database import SessionLocal
from app.models.user import User, UserRole


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote a verified Lumen account to admin.")
    parser.add_argument("email", help="Email of the existing, verified account to promote")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if not email:
        parser.error("email must not be empty")

    db = SessionLocal()
    try:
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user is None:
            print("Account not found. Register the account first.", file=sys.stderr)
            return 1
        if not user.is_active:
            print("Inactive accounts cannot be promoted.", file=sys.stderr)
            return 1
        if not user.is_email_verified:
            print("Verify the account email before promoting it.", file=sys.stderr)
            return 1
        if user.role == UserRole.admin:
            print(f"{user.email} already has the admin role.")
            return 0

        user.role = UserRole.admin
        db.commit()
        print(f"Granted admin role to verified account {user.email}.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
