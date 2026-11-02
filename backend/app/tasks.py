"""
مهام خلفية (Celery) — إرسال الإيميل بالخصوص، عشان ما يبطّئ الرد على الطلب بانتظار SMTP.

لو مكتبة celery غير مثبّتة، أو Redis/الـ worker مو شغّالين، queue_email() ترجع
تلقائيًا للإرسال المباشر (sync) بدل ما تفشل الطلب كامل — التطبيق يشتغل حتى بدون
Celery مضبوط، بس بدون فايدة "الخلفية" وقتها.
"""
from app.logging_config import get_logger
from app.services.email_service import send_email

logger = get_logger("tasks")

try:
    from celery import Celery
    from celery.schedules import crontab

    from app.config import settings

    celery_app = Celery(
        "lumen_backend",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    # جدولة Celery beat — يحتاج تشغيل worker إضافي بوضع beat (راجع docker-compose.yml)
    celery_app.conf.beat_schedule = {
        "weekly-progress-digest": {
            "task": "send_weekly_digests_task",
            "schedule": crontab(hour=8, minute=0, day_of_week=0),  # كل أحد 8 صباحًا
        },
        "daily-due-cards-reminder": {
            "task": "send_due_cards_reminders_task",
            "schedule": crontab(hour=18, minute=0),  # يوميًا 6 مساءً
        },
    }

    @celery_app.task(name="send_email_task")
    def send_email_task(to: str, subject: str, body: str) -> None:
        send_email(to, subject, body)

    @celery_app.task(name="send_weekly_digests_task")
    def send_weekly_digests_task() -> None:
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.reports import build_progress_report, format_report_email_body

        db = SessionLocal()
        try:
            for user in db.query(User).filter(User.is_active.is_(True)).all():
                report = build_progress_report(db, user.id)
                if report["topics_practiced"] == 0:
                    continue  # ما فيه نشاط بعد — ما نزعج مستخدم لسه ما بدأ
                send_email(user.email, "ملخص تقدّمك الأسبوعي", format_report_email_body(report))
        finally:
            db.close()

    @celery_app.task(name="send_due_cards_reminders_task")
    def send_due_cards_reminders_task() -> None:
        from datetime import datetime, timezone

        from app.database import SessionLocal
        from app.models.review_card import ReviewCard
        from app.models.user import User
        from app.notifications import notify

        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            user_ids_with_due_cards = (
                db.query(ReviewCard.user_id)
                .filter(ReviewCard.due_at <= now)
                .distinct()
                .all()
            )
            for (user_id,) in user_ids_with_due_cards:
                user = db.get(User, user_id)
                if user and user.is_active:
                    notify(
                        db, user_id, "بطاقات مراجعة بانتظارك",
                        "عندك بطاقات تكرار متباعد مستحقة اليوم — راجعها قبل ما تنسى المحتوى",
                        "reminder",
                    )
        finally:
            db.close()

    _CELERY_AVAILABLE = True
except ImportError:
    celery_app = None
    send_email_task = None
    _CELERY_AVAILABLE = False
    logger.info("مكتبة celery غير مثبّتة — الإيميلات تُرسل مباشرة (sync) بدون طابور خلفي")


def queue_email(to: str, subject: str, body: str) -> None:
    """يحاول جدولة الإيميل عبر Celery؛ لو مو متاح أو فشل الاتصال بـ Redis، يرسله مباشرة"""
    if _CELERY_AVAILABLE:
        try:
            send_email_task.delay(to, subject, body)
            return
        except Exception:
            logger.warning("تعذر إرسال المهمة لـ Celery/Redis — إرسال مباشر بدلها")
    send_email(to, subject, body)
