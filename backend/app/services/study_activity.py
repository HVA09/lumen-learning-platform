"""
تسجيل النشاط الدراسي اليومي وقراءة الـ streak — تُستدعى بعد أي نشاط تعليمي حقيقي
(تسليم اختبار، مراجعة بطاقة، إنهاء درس). اليوم يُحسب بتوقيت UTC.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.study_day import StudyDay
from app.modules.learning_progress.domain.streak_logic import compute_streak

STREAK_LOOKBACK_DAYS = 400


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def record_study_activity(db: Session, user_id: int, today: date | None = None) -> None:
    """يسجّل إن الطالب درس اليوم (مرة وحدة باليوم مهما تكرر النشاط)"""
    today = today or _utc_today()
    already = (
        db.query(StudyDay.id).filter(StudyDay.user_id == user_id, StudyDay.day == today).first()
    )
    if already:
        return
    try:
        with db.begin_nested():
            db.add(StudyDay(user_id=user_id, day=today))
    except IntegrityError:
        pass  # طلب ثاني سجّل نفس اليوم بنفس اللحظة — نتيجتها نفس المطلوب
    db.commit()


def get_study_streak(db: Session, user_id: int, today: date | None = None) -> int:
    today = today or _utc_today()
    since = today - timedelta(days=STREAK_LOOKBACK_DAYS)
    rows = (
        db.query(StudyDay.day).filter(StudyDay.user_id == user_id, StudyDay.day >= since).all()
    )
    return compute_streak({row[0] for row in rows}, today)


def studied_today(db: Session, user_id: int, today: date | None = None) -> bool:
    today = today or _utc_today()
    return (
        db.query(StudyDay.id).filter(StudyDay.user_id == user_id, StudyDay.day == today).first()
        is not None
    )
