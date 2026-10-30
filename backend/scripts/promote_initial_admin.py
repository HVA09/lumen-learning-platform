"""
ترقية حساب موجود إلى admin من بيئة الخادم فقط.

الاستخدام من مجلد backend:
    python scripts/promote_initial_admin.py --email owner@example.com

لا يوجد endpoint عام لترقية المدير. يتطلب الأمر تأكيد البريد تفاعليًا،
ويرفض العمل إذا كان هناك مدير بالفعل أو كان الحساب غير موجود/معطّل.
"""
import argparse
import sys

from sqlalchemy import text

from app.database import SessionLocal
from app.models.user import User, UserRole


def promote_initial_admin(email: str, confirmation: str) -> None:
    normalized_email = email.strip().lower()
    if not normalized_email or confirmation.strip().lower() != normalized_email:
        raise ValueError("لم يتطابق تأكيد البريد الإلكتروني؛ لم يتم إجراء أي تغيير.")

    with SessionLocal() as db:
        with db.begin():
            # قفل PostgreSQL يمنع تنفيذ عمليتي bootstrap متزامنتين.
            db.execute(text("SELECT pg_advisory_xact_lock(731904221)"))

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
            user.role = UserRole.admin

    print(f"تمت ترقية {normalized_email} إلى admin بنجاح.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Securely promote the first Lumen admin.")
    parser.add_argument("--email", required=True, help="Email address of the existing account")
    args = parser.parse_args()

    confirmation = input(
        f"سيتم منح صلاحية المدير للحساب {args.email}. اكتب البريد نفسه للتأكيد: "
    )
    try:
        promote_initial_admin(args.email, confirmation)
    except Exception as exc:
        print(f"فشل ترقية المدير: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
