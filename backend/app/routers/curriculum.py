"""
مسارات المنهج: عرض المواد والمواضيع، مسار الطالب (حالة كل موضوع والموضوع المقترح)،
دروس كل موضوع، وإنهاء الدروس.

إتقان الطالب يُحسب بالسيرفر فقط من نتائج الاختبارات (راجع routers/quiz.py) — ما فيه مسار
يقبل نسبة إتقان من المتصفح.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.lesson import Lesson, LessonProgress
from app.models.question import Question
from app.models.subject import Subject
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.user import User
from app.schemas.curriculum import (
    LearningPathOut,
    LessonCompleteOut,
    LessonOut,
    MasteryOut,
    SubjectWithTopicsOut,
    TopicOut,
    UnlockedAchievementOut,
)
from app.services.achievements import check_and_award_achievements
from app.services.learning_path import build_learning_path
from app.services.study_activity import record_study_activity

router = APIRouter(prefix="/curriculum", tags=["Curriculum"])


@router.get("/subjects", response_model=list[SubjectWithTopicsOut])
def list_subjects(db: Session = Depends(get_db)):
    return (
        db.query(Subject)
        .options(selectinload(Subject.topics))
        .filter(Subject.is_active.is_(True))
        .order_by(Subject.order_index)
        .all()
    )


@router.get("/path", response_model=LearningPathOut)
def get_my_learning_path(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """مسار الطالب بطلب واحد: حالة كل موضوع (مقفل/متاح/قيد الدراسة/متقن)، الإتقان، تقدّم الدروس،
    والموضوع المقترح للخطوة التالية — يغني الواجهة عن طلب إتقان لكل موضوع لحاله"""
    subjects = (
        db.query(Subject)
        .options(selectinload(Subject.topics))
        .filter(Subject.is_active.is_(True))
        .order_by(Subject.order_index)
        .all()
    )
    subject_dicts = [
        {
            "id": s.id,
            "slug": s.slug,
            "name_ar": s.name_ar,
            "name_en": s.name_en,
            "topics": [
                {
                    "id": t.id,
                    "slug": t.slug,
                    "name_ar": t.name_ar,
                    "name_en": t.name_en,
                    "learning_outcomes_ar": t.learning_outcomes_ar,
                    "simulation_type": t.simulation_type,
                    "prerequisite_topic_id": t.prerequisite_topic_id,
                }
                for t in s.topics
            ],
        }
        for s in subjects
    ]

    mastery = {
        m.topic_id: {
            "mastery_percentage": m.mastery_percentage,
            "gateway_quiz_passed": m.gateway_quiz_passed,
            "attempts_count": m.attempts_count,
        }
        for m in db.query(TopicMastery).filter(TopicMastery.user_id == current_user.id).all()
    }
    lessons_total = dict(
        db.query(Lesson.topic_id, func.count(Lesson.id))
        .filter(Lesson.is_published.is_(True))
        .group_by(Lesson.topic_id)
        .all()
    )
    lessons_done = dict(
        db.query(Lesson.topic_id, func.count(LessonProgress.id))
        .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
        .filter(LessonProgress.user_id == current_user.id, Lesson.is_published.is_(True))
        .group_by(Lesson.topic_id)
        .all()
    )
    questions_count = dict(
        db.query(Question.topic_id, func.count(Question.id))
        .filter(Question.is_active.is_(True))
        .group_by(Question.topic_id)
        .all()
    )
    return build_learning_path(subject_dicts, mastery, lessons_total, lessons_done, questions_count)


@router.get("/topics/{topic_id}", response_model=TopicOut)
def get_topic(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموضوع غير موجود")
    return topic


@router.get("/topics/{topic_id}/mastery", response_model=MasteryOut)
def get_my_mastery(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mastery = (
        db.query(TopicMastery)
        .filter(TopicMastery.user_id == current_user.id, TopicMastery.topic_id == topic_id)
        .first()
    )
    if not mastery:
        # ولا محاولة لسه — نرجّع صفر بدل 404 عشان الفرونت اند ما يحتاج يتعامل مع حالة خاصة
        return MasteryOut(
            topic_id=topic_id, mastery_percentage=0.0, gateway_quiz_passed=False,
            attempts_count=0, last_practiced_at=None,
        )
    return mastery


@router.get("/topics/{topic_id}/lessons", response_model=list[LessonOut])
def list_topic_lessons(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not db.get(Topic, topic_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموضوع غير موجود")

    lessons = (
        db.query(Lesson)
        .filter(Lesson.topic_id == topic_id, Lesson.is_published.is_(True))
        .order_by(Lesson.order_index, Lesson.id)
        .all()
    )
    completed_ids: set[int] = set()
    if lessons:
        completed_ids = {
            row[0]
            for row in db.query(LessonProgress.lesson_id)
            .filter(
                LessonProgress.user_id == current_user.id,
                LessonProgress.lesson_id.in_([lesson.id for lesson in lessons]),
            )
            .all()
        }
    return [
        LessonOut(
            id=lesson.id,
            topic_id=lesson.topic_id,
            slug=lesson.slug,
            title_ar=lesson.title_ar,
            body_md=lesson.body_md,
            estimated_minutes=lesson.estimated_minutes,
            order_index=lesson.order_index,
            completed=lesson.id in completed_ids,
        )
        for lesson in lessons
    ]


@router.post("/lessons/{lesson_id}/complete", response_model=LessonCompleteOut)
def complete_lesson(
    lesson_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """يسجّل إن الطالب أنهى الدرس — آمن لو تكرر الطلب (ما ينشئ سجلًا ثانيًا)"""
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.is_published:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير موجود")

    already_done = (
        db.query(LessonProgress.id)
        .filter(LessonProgress.user_id == current_user.id, LessonProgress.lesson_id == lesson_id)
        .first()
    )
    if not already_done:
        try:
            with db.begin_nested():
                db.add(LessonProgress(user_id=current_user.id, lesson_id=lesson_id))
        except IntegrityError:
            pass  # طلب ثاني سجّله بنفس اللحظة
        db.commit()

    record_study_activity(db, current_user.id)
    unlocked = check_and_award_achievements(db, current_user.id)
    return LessonCompleteOut(
        lesson_id=lesson_id,
        completed=True,
        new_achievements=[UnlockedAchievementOut(key=a.key, title_ar=a.title_ar) for a in unlocked],
    )
