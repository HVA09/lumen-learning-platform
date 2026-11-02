"""
تقرير تقدّم الطالب — يُستخدم لعرض لوحة "تقدّمي" وللإيميل الأسبوعي/تقرير ولي الأمر.
دالة تجمع بيانات من كل أجزاء Lumen بدون تعديل أي شيء.
"""
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assignment import AssignmentSubmission
from app.models.lesson import LessonProgress
from app.models.quiz_attempt import QuizAttempt
from app.models.review_card import ReviewCard
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.user import User
from app.models.user_achievement import UserAchievement
from app.services.study_activity import get_study_streak

WEAK_MASTERY_THRESHOLD = 50.0


def build_progress_report(db: Session, user_id: int) -> dict:
    user = db.get(User, user_id)
    masteries = db.query(TopicMastery).filter(TopicMastery.user_id == user_id).all()

    average_mastery = (
        sum(m.mastery_percentage for m in masteries) / len(masteries) if masteries else 0.0
    )
    gateway_passed = sum(1 for m in masteries if m.gateway_quiz_passed)

    weak_topic_ids = [m.topic_id for m in masteries if m.mastery_percentage < WEAK_MASTERY_THRESHOLD]
    weak_topics = (
        db.query(Topic.name_ar).filter(Topic.id.in_(weak_topic_ids)).all() if weak_topic_ids else []
    )

    achievements_count = (
        db.query(func.count(UserAchievement.id)).filter(UserAchievement.user_id == user_id).scalar()
    )

    now = datetime.now(timezone.utc)
    cards_due_now = (
        db.query(func.count(ReviewCard.id))
        .filter(ReviewCard.user_id == user_id, ReviewCard.due_at <= now)
        .scalar()
    )
    leech_cards = (
        db.query(func.count(ReviewCard.id))
        .filter(ReviewCard.user_id == user_id, ReviewCard.is_leech.is_(True))
        .scalar()
    )

    assignments_submitted = (
        db.query(func.count(AssignmentSubmission.id))
        .filter(AssignmentSubmission.student_user_id == user_id)
        .scalar()
    )

    quizzes_taken, average_quiz_score = (
        db.query(func.count(QuizAttempt.id), func.avg(QuizAttempt.score_percentage))
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.submitted_at.is_not(None))
        .one()
    )
    lessons_completed = (
        db.query(func.count(LessonProgress.id)).filter(LessonProgress.user_id == user_id).scalar()
    )

    return {
        "user_email": user.email if user else None,
        "topics_practiced": len(masteries),
        "average_mastery": round(average_mastery, 1),
        "gateway_quizzes_passed": gateway_passed,
        "weak_topics": [t[0] for t in weak_topics],
        "achievements_unlocked": achievements_count,
        "cards_due_now": cards_due_now,
        "leech_cards": leech_cards,
        "assignments_submitted": assignments_submitted,
        "quizzes_taken": quizzes_taken,
        "average_quiz_score": round(float(average_quiz_score), 1) if average_quiz_score else 0.0,
        "lessons_completed": lessons_completed,
        "streak_days": get_study_streak(db, user_id),
    }


def format_report_email_body(report: dict) -> str:
    weak_line = (
        f"مواضيع تحتاج تركيز أكثر: {', '.join(report['weak_topics'])}"
        if report["weak_topics"]
        else "ما فيه مواضيع ضعيفة حاليًا — أداء جيد بشكل عام"
    )
    return (
        f"ملخص التقدّم الأسبوعي:\n\n"
        f"- متوسط الإتقان: {report['average_mastery']}%\n"
        f"- بوابات إتقان مجتازة: {report['gateway_quizzes_passed']}\n"
        f"- اختبارات مسلَّمة: {report['quizzes_taken']} (متوسط الدرجة {report['average_quiz_score']}%)\n"
        f"- دروس منجزة: {report['lessons_completed']}\n"
        f"- أيام دراسة متتالية: {report['streak_days']}\n"
        f"- إنجازات مفتوحة: {report['achievements_unlocked']}\n"
        f"- واجبات مُسلَّمة: {report['assignments_submitted']}\n"
        f"- بطاقات مراجعة مستحقة الآن: {report['cards_due_now']}\n"
        f"- {weak_line}"
    )
