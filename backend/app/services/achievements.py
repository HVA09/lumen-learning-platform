"""
تعريفات الإنجازات (ثابتة بالكود) + منطق فتحها + حساب نقاط لوحة المتصدرين.

كل الشروط تُحسب من بيانات يتحقق منها السيرفر نفسه (اختبارات مصحَّحة بالسيرفر، واجبات قيّمها
معلّم، أيام دراسة مسجّلة) — ما فيه أي إنجاز أو نقطة تعتمد على رقم يرسله المتصفح.
"""
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assignment import AssignmentSubmission
from app.models.lesson import LessonProgress
from app.models.quiz_attempt import QuizAttempt
from app.models.review_card import ReviewCard
from app.models.topic_mastery import TopicMastery
from app.models.user_achievement import UserAchievement
from app.services.study_activity import get_study_streak

PASSING_ASSIGNMENT_PERCENTAGE = 70

# نقاط لوحة المتصدرين
POINTS_PER_GATEWAY_PASSED = 20
POINTS_PER_PASSING_ASSIGNMENT = 15
POINTS_PER_TEN_MASTERY_PERCENT = 1  # كل 10% إتقان بموضوع = نقطة (حتى 10 نقاط للموضوع)
POINTS_PER_REVIEWED_CARD = 2
MAX_REVIEWED_CARDS_FOR_POINTS = 25  # سقف يمنع تكديس النقاط بإنشاء بطاقات كثيرة


@dataclass
class AchievementDef:
    key: str
    title_ar: str
    description_ar: str
    condition: Callable[[Session, int], bool]


def _gateway_quizzes_passed_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(TopicMastery.id))
        .filter(TopicMastery.user_id == user_id, TopicMastery.gateway_quiz_passed.is_(True))
        .scalar()
    )


def _passing_assignments_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(AssignmentSubmission.id))
        .filter(
            AssignmentSubmission.student_user_id == user_id,
            AssignmentSubmission.grade_percentage >= PASSING_ASSIGNMENT_PERCENTAGE,
        )
        .scalar()
    )


def _reviewed_cards_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(ReviewCard.id))
        .filter(ReviewCard.user_id == user_id, ReviewCard.repetitions > 0)
        .scalar()
    )


def _submitted_quizzes_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(QuizAttempt.id))
        .filter(QuizAttempt.user_id == user_id, QuizAttempt.submitted_at.is_not(None))
        .scalar()
    )


def _has_perfect_quiz(db: Session, user_id: int) -> bool:
    return (
        db.query(QuizAttempt.id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.submitted_at.is_not(None),
            QuizAttempt.score_percentage >= 100,
        )
        .first()
        is not None
    )


def _completed_lessons_count(db: Session, user_id: int) -> int:
    return (
        db.query(func.count(LessonProgress.id)).filter(LessonProgress.user_id == user_id).scalar()
    )


ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef(
        "first_lesson", "بداية المعرفة", "أنهيت أول درس",
        lambda db, uid: _completed_lessons_count(db, uid) >= 1,
    ),
    AchievementDef(
        "first_quiz", "أول اختبار", "سلّمت أول اختبار تدريبي أو اختبار بوابة",
        lambda db, uid: _submitted_quizzes_count(db, uid) >= 1,
    ),
    AchievementDef(
        "perfect_quiz", "علامة كاملة", "حصلت على 100% في اختبار",
        lambda db, uid: _has_perfect_quiz(db, uid),
    ),
    AchievementDef(
        "first_review", "أول خطوة", "راجعت أول بطاقة تكرار متباعد",
        lambda db, uid: _reviewed_cards_count(db, uid) >= 1,
    ),
    AchievementDef(
        "gateway_first", "بوابة مفتوحة", "اجتزت أول اختبار بوابة إتقان",
        lambda db, uid: _gateway_quizzes_passed_count(db, uid) >= 1,
    ),
    AchievementDef(
        "gateway_five", "طالب مجتهد", "اجتزت 5 اختبارات بوابة إتقان",
        lambda db, uid: _gateway_quizzes_passed_count(db, uid) >= 5,
    ),
    AchievementDef(
        "assignment_first", "واجب مُنجز", "أنجزت أول واجب بنتيجة 70% فأكثر",
        lambda db, uid: _passing_assignments_count(db, uid) >= 1,
    ),
    AchievementDef(
        "assignment_expert", "خبير", "أنجزت 3 واجبات بنتيجة 70% فأكثر",
        lambda db, uid: _passing_assignments_count(db, uid) >= 3,
    ),
    AchievementDef(
        "streak_3", "ثلاثة أيام متتالية", "درست 3 أيام متتالية",
        lambda db, uid: get_study_streak(db, uid) >= 3,
    ),
    AchievementDef(
        "streak_7", "أسبوع من الالتزام", "درست 7 أيام متتالية",
        lambda db, uid: get_study_streak(db, uid) >= 7,
    ),
]


def check_and_award_achievements(db: Session, user_id: int) -> list[AchievementDef]:
    """يفحص كل الإنجازات، يفتح أي وحدة جديدة تحققت، ويرجّع قائمة الإنجازات
    المفتوحة حديثًا بهذي المرة (فاضية لو ما فيه جديد)"""
    already_unlocked = {
        row[0]
        for row in db.query(UserAchievement.achievement_key)
        .filter(UserAchievement.user_id == user_id)
        .all()
    }

    newly_unlocked = []
    for achievement in ACHIEVEMENTS:
        if achievement.key in already_unlocked:
            continue
        if achievement.condition(db, user_id):
            db.add(UserAchievement(user_id=user_id, achievement_key=achievement.key))
            newly_unlocked.append(achievement)

    if newly_unlocked:
        db.commit()
    return newly_unlocked


def compute_scores(db: Session, user_id: int | None = None) -> dict[int, int]:
    """نقاط اللوحة لكل الطلاب (أو لطالب واحد) بأربعة استعلامات مجمّعة فقط — بدل استعلامات
    لكل مستخدم. الطلاب اللي نقاطهم صفر ما يظهرون بالنتيجة.

    النقاط: 20 لكل بوابة إتقان مجتازة + 15 لكل واجب ناجح (≥70% قيّمه معلّم)
    + نقطة لكل 10% إتقان بكل موضوع + نقطتان لكل بطاقة تحت مراجعة فعلية (حتى 25 بطاقة)"""
    scores: dict[int, int] = {}

    def _add(uid: int, points: int) -> None:
        scores[uid] = scores.get(uid, 0) + int(points)

    gateway_query = db.query(TopicMastery.user_id, func.count(TopicMastery.id)).filter(
        TopicMastery.gateway_quiz_passed.is_(True)
    )
    mastery_query = db.query(
        TopicMastery.user_id, func.sum(func.floor(TopicMastery.mastery_percentage / 10.0))
    )
    assignments_query = db.query(
        AssignmentSubmission.student_user_id, func.count(AssignmentSubmission.id)
    ).filter(AssignmentSubmission.grade_percentage >= PASSING_ASSIGNMENT_PERCENTAGE)
    cards_query = db.query(ReviewCard.user_id, func.count(ReviewCard.id)).filter(
        ReviewCard.repetitions > 0
    )

    if user_id is not None:
        gateway_query = gateway_query.filter(TopicMastery.user_id == user_id)
        mastery_query = mastery_query.filter(TopicMastery.user_id == user_id)
        assignments_query = assignments_query.filter(
            AssignmentSubmission.student_user_id == user_id
        )
        cards_query = cards_query.filter(ReviewCard.user_id == user_id)

    for uid, count in gateway_query.group_by(TopicMastery.user_id).all():
        _add(uid, count * POINTS_PER_GATEWAY_PASSED)
    for uid, total in mastery_query.group_by(TopicMastery.user_id).all():
        _add(uid, (total or 0) * POINTS_PER_TEN_MASTERY_PERCENT)
    for uid, count in assignments_query.group_by(AssignmentSubmission.student_user_id).all():
        _add(uid, count * POINTS_PER_PASSING_ASSIGNMENT)
    for uid, count in cards_query.group_by(ReviewCard.user_id).all():
        _add(uid, min(count, MAX_REVIEWED_CARDS_FOR_POINTS) * POINTS_PER_REVIEWED_CARD)

    return {uid: points for uid, points in scores.items() if points > 0}


def compute_leaderboard_score(db: Session, user_id: int) -> int:
    return compute_scores(db, user_id).get(user_id, 0)
