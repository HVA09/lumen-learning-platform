"""
مسارات التحفيز: لوحة المتصدرين (نقاط محسوبة من بيانات يتحقق منها السيرفر) وإنجازات الطالب وإحصائياته
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.class_section import ClassEnrollment, ClassSection
from app.models.user import User, UserRole
from app.models.user_achievement import UserAchievement
from app.schemas.gamification import AchievementOut, LeaderboardEntryOut, MyStatsOut
from app.services.achievements import ACHIEVEMENTS, compute_scores
from app.services.study_activity import get_study_streak, studied_today

router = APIRouter(prefix="/gamification", tags=["Gamification"])


def _display_name(user_id: int, full_name: str | None) -> str:
    """ما نعرض جزء من الإيميل أبدًا — الاسم الكامل لو موجود، وإلا رقم مجهول"""
    return full_name.strip() if full_name and full_name.strip() else f"طالب {user_id}"


def _class_member_ids(db: Session, class_id: int) -> set[int]:
    return {
        row[0]
        for row in db.query(ClassEnrollment.student_user_id)
        .filter(ClassEnrollment.class_section_id == class_id)
        .all()
    }


def _ensure_can_view_class_leaderboard(class_id: int, user: User, db: Session) -> None:
    class_section = db.get(ClassSection, class_id)
    if not class_section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفصل غير موجود")
    if user.role == UserRole.admin or class_section.teacher_user_id == user.id:
        return
    if user.id not in _class_member_ids(db, class_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="لوحة متصدرين هذا الفصل لطلابه فقط"
        )


def _ranked_students(db: Session, class_id: int | None = None) -> list[tuple[int, str, int]]:
    """الطلاب الفعّالون اللي عندهم نقاط، مرتّبين من الأعلى: (user_id, الاسم المعروض, النقاط)
    — class_id يحصر النتيجة بطلاب فصل معيّن بدل كل المنصة"""
    scores = compute_scores(db)
    if not scores:
        return []
    query = db.query(User.id, User.full_name).filter(
        User.id.in_(list(scores)),
        User.is_active.is_(True),
        User.role == UserRole.user,
    )
    if class_id is not None:
        member_ids = _class_member_ids(db, class_id)
        if not member_ids:
            return []
        query = query.filter(User.id.in_(member_ids))
    students = query.all()
    ranked = [(uid, _display_name(uid, name), scores[uid]) for uid, name in students]
    ranked.sort(key=lambda row: (-row[2], row[0]))
    return ranked


@router.get("/leaderboard", response_model=list[LeaderboardEntryOut])
def get_leaderboard(
    limit: int = 20,
    class_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if class_id is not None:
        _ensure_can_view_class_leaderboard(class_id, current_user, db)
    ranked = _ranked_students(db, class_id)
    return [
        LeaderboardEntryOut(
            user_id=uid,
            display_name=name,
            score=score,
            rank=rank,
            is_me=uid == current_user.id,
        )
        for rank, (uid, name, score) in enumerate(ranked[: max(1, min(limit, 100))], start=1)
    ]


@router.get("/my-stats", response_model=MyStatsOut)
def get_my_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ranked = _ranked_students(db)
    rank = next((i for i, (uid, _, _) in enumerate(ranked, start=1) if uid == current_user.id), None)
    score = next((s for uid, _, s in ranked if uid == current_user.id), 0)
    if rank is None:
        # معلّم/admin أو طالب بدون نقاط: نعرض نقاطه الفعلية بدون ترتيب
        score = compute_scores(db, current_user.id).get(current_user.id, 0)
    return MyStatsOut(
        score=score,
        rank=rank,
        streak_days=get_study_streak(db, current_user.id),
        studied_today=studied_today(db, current_user.id),
    )


@router.get("/my-achievements", response_model=list[AchievementOut])
def get_my_achievements(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    unlocked = {
        row.achievement_key: row.unlocked_at
        for row in db.query(UserAchievement).filter(UserAchievement.user_id == current_user.id).all()
    }
    return [
        AchievementOut(
            key=a.key, title_ar=a.title_ar, description_ar=a.description_ar,
            unlocked_at=unlocked.get(a.key),
        )
        for a in ACHIEVEMENTS
    ]
