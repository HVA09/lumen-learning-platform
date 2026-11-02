"""
مسارات تقرير التقدّم: عرض ملخص شخصي، أو إرسال نسخة بالإيميل فورًا (بدل انتظار
الجدولة الأسبوعية بـ Celery beat) — مفيدة لولي الأمر أو الطالب نفسه
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.email_service import send_progress_report_email
from app.services.reports import build_progress_report, format_report_email_body

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/my-progress")
def get_my_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_progress_report(db, current_user.id)


@router.post("/send-my-report")
def send_my_report(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = build_progress_report(db, current_user.id)
    send_progress_report_email(current_user.email, format_report_email_body(report))
    return {"detail": "تم إرسال التقرير لبريدك الإلكتروني"}
