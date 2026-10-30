"""
ترقية حساب موجود إلى admin من بيئة الخادم فقط.

الاستخدام من مجلد backend:
    python scripts/promote_initial_admin.py --email owner@example.com

يجب إنشاء الحساب وتأكيد بريده أولًا. لا يوجد endpoint عام لترقية المدير.
يرفض الأمر العمل إذا كان هناك مدير بالفعل أو كان الحساب غير موجود/معطّل/غير مؤكد.
"""
import argparse
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, UserRole

ADMIN_BOOTSTRAP_LOCK_ID = 731904221


def promote_initial_admin(db: Session, email: str, confirmation: str) -> None:
    """Grant the first admin role inside the caller's database transaction."""
    normalized_email = email.strip().lower()
    if not normalized_email or confirmation.strip().lower() != normalized_email:
        raise ValueError("لم يتطابق تأكيد البريد الإلكتروني؛ لم يتم إجراء أي تغيير.")

    # قفل PostgreSQL يمنع تنفيذ عمليتي bootstrap متزامنتين.
    db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": ADMIN_BOOTSTRAP_LOCK_ID})

    existing_admin = db.query(User.id).filter(User.role == UserRole.admin).first()
    if existing_admin:
        raise ValueError(
            "يوجد مدير بالفعل. أوقف الأمر واستخدم لوحة الإدارة لترقية الحسابات لاحقًا."
        )

    user = db.query(User).filter(User.email == normalized_email).with_for_update().first()
    if user is None:
        raise ValueError("الحساب غير موجود. أنشئ الحساب أولًا من واجهة التسجيل.")
    if not user.is_active:
        raise ValueError("الحساب معطّل؛ لا يمكن ترقيته إلى مدير.")
    if not user.is_email_verified:
        raise ValueError("يجب تأكيد البريد الإلكتروني للحساب قبل منحه صلاحية المدير.")

    user.role = UserRole.admin
    db.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Securely promote the first Lumen admin.")
    parser.add_argument("--email", required=True, help="Email address of the existing account")
    args = parser.parse_args()

    confirmation = input(
        f"سيتم منح صلاحية المدير للحساب {args.email}. اكتب البريد نفسه للتأكيد: "
    )
    try:
        with SessionLocal() as db:
            with db.begin():
                promote_initial_admin(db, args.email, confirmation)
        print(f"تمت ترقية {args.email.strip().lower()} إلى admin بنجاح.")
    except Exception as exc:
        print(f"فشل ترقية المدير: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
