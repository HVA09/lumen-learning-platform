"""
مسارات إدارة المحتوى (معلّم أو admin): دروس المواضيع وبنك الأسئلة.
الطالب ما يستخدم هذي المسارات أبدًا — هي الوحيدة اللي ترجّع الإجابات الصحيحة قبل التسليم.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.audit import log_event
from app.database import get_db
from app.dependencies import require_teacher
from app.models.lesson import Lesson
from app.models.question import Question
from app.models.question_result import QuestionResult
from app.models.topic import Topic
from app.models.user import User
from app.schemas.content import (
    LessonAdminOut,
    LessonCreate,
    QuestionAdminOut,
    QuestionAnalyticsOut,
    QuestionCreate,
)
from app.services.question_analytics import (
    FLAG_LABELS_AR,
    classify_question,
    most_common_wrong_answer,
    sort_for_review,
    success_rate,
)
from app.modules.assessments.domain.quiz_logic import coerce_bool, coerce_int

router = APIRouter(prefix="/content", tags=["Content"])


def _get_topic_or_404(topic_id: int, db: Session) -> Topic:
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموضوع غير موجود")
    return topic


def _get_question_or_404(question_id: int, db: Session) -> Question:
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="السؤال غير موجود")
    return question


def _get_lesson_or_404(lesson_id: int, db: Session) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الدرس غير موجود")
    return lesson


# ---------- الأسئلة ----------

@router.get("/topics/{topic_id}/questions", response_model=list[QuestionAdminOut])
def list_questions(
    topic_id: int, _: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    _get_topic_or_404(topic_id, db)
    return db.query(Question).filter(Question.topic_id == topic_id).order_by(Question.id).all()


@router.post(
    "/topics/{topic_id}/questions",
    response_model=QuestionAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    topic_id: int,
    payload: QuestionCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    _get_topic_or_404(topic_id, db)
    question = Question(
        topic_id=topic_id,
        kind=payload.kind,
        prompt_ar=payload.prompt_ar,
        choices=payload.choices,
        correct_answer=payload.correct_answer,
        tolerance=payload.tolerance,
        explanation_ar=payload.explanation_ar,
        difficulty=payload.difficulty,
        is_active=payload.is_active,
        created_by_user_id=teacher.id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    log_event(db, "question_created", f"{teacher.email} أضاف سؤالًا #{question.id} للموضوع {topic_id}", teacher.id)
    return question


@router.put("/questions/{question_id}", response_model=QuestionAdminOut)
def update_question(
    question_id: int,
    payload: QuestionCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(question_id, db)
    question.kind = payload.kind
    question.prompt_ar = payload.prompt_ar
    question.choices = payload.choices
    question.correct_answer = payload.correct_answer
    question.tolerance = payload.tolerance
    question.explanation_ar = payload.explanation_ar
    question.difficulty = payload.difficulty
    question.is_active = payload.is_active
    db.commit()
    db.refresh(question)
    log_event(db, "question_updated", f"{teacher.email} عدّل السؤال #{question.id}", teacher.id)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    question = _get_question_or_404(question_id, db)
    db.delete(question)
    db.commit()
    log_event(db, "question_deleted", f"{teacher.email} حذف السؤال #{question_id}", teacher.id)


# ---------- الدروس ----------

@router.get("/topics/{topic_id}/lessons", response_model=list[LessonAdminOut])
def list_lessons(topic_id: int, _: User = Depends(require_teacher), db: Session = Depends(get_db)):
    _get_topic_or_404(topic_id, db)
    return (
        db.query(Lesson)
        .filter(Lesson.topic_id == topic_id)
        .order_by(Lesson.order_index, Lesson.id)
        .all()
    )


@router.post(
    "/topics/{topic_id}/lessons",
    response_model=LessonAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    topic_id: int,
    payload: LessonCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    _get_topic_or_404(topic_id, db)
    lesson = Lesson(
        topic_id=topic_id,
        slug=f"lesson-{uuid.uuid4().hex[:8]}",
        title_ar=payload.title_ar,
        body_md=payload.body_md,
        estimated_minutes=payload.estimated_minutes,
        order_index=payload.order_index,
        is_published=payload.is_published,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    log_event(db, "lesson_created", f"{teacher.email} أضاف درسًا #{lesson.id} للموضوع {topic_id}", teacher.id)
    return lesson


@router.put("/lessons/{lesson_id}", response_model=LessonAdminOut)
def update_lesson(
    lesson_id: int,
    payload: LessonCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    lesson = _get_lesson_or_404(lesson_id, db)
    lesson.title_ar = payload.title_ar
    lesson.body_md = payload.body_md
    lesson.estimated_minutes = payload.estimated_minutes
    lesson.order_index = payload.order_index
    lesson.is_published = payload.is_published
    db.commit()
    db.refresh(lesson)
    log_event(db, "lesson_updated", f"{teacher.email} عدّل الدرس #{lesson.id}", teacher.id)
    return lesson


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    lesson = _get_lesson_or_404(lesson_id, db)
    db.delete(lesson)
    db.commit()
    log_event(db, "lesson_deleted", f"{teacher.email} حذف الدرس #{lesson_id}", teacher.id)


# ---------- تحليل الأسئلة ----------

def _normalize_choice_answer(kind: str, given):
    """يوحّد شكل إجابة الطالب قبل عدّ تكرارها (2 و "2" نفس الخيار) — وغير المفهوم يُهمَل"""
    if kind == "mcq":
        return coerce_int(given)
    if kind == "true_false":
        return coerce_bool(given)
    return given


@router.get("/topics/{topic_id}/analytics", response_model=list[QuestionAnalyticsOut])
def get_topic_question_analytics(
    topic_id: int, _: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    """أداء الطلاب الفعلي بكل سؤال بالموضوع (نسبة النجاح، وأكثر إجابة خاطئة تكرارًا) مع تنبيه
    للأسئلة اللي تحتاج مراجعة — الأسئلة الأضعف أداءً أولًا"""
    _get_topic_or_404(topic_id, db)

    questions = db.query(Question).filter(Question.topic_id == topic_id).all()
    if not questions:
        return []
    question_ids = [q.id for q in questions]

    totals = {
        row.question_id: (row.answered, int(row.correct or 0))
        for row in db.query(
            QuestionResult.question_id,
            func.count(QuestionResult.id).label("answered"),
            func.sum(case((QuestionResult.correct.is_(True), 1), else_=0)).label("correct"),
        )
        .filter(QuestionResult.question_id.in_(question_ids))
        .group_by(QuestionResult.question_id)
        .all()
    }

    wrong_answers: dict[int, list] = {}
    kinds_by_id = {q.id: q.kind for q in questions}
    choice_kinds = {q.id for q in questions if q.kind in ("mcq", "true_false")}
    if choice_kinds:
        for question_id, given in (
            db.query(QuestionResult.question_id, QuestionResult.given_answer)
            .filter(
                QuestionResult.question_id.in_(choice_kinds),
                QuestionResult.correct.is_(False),
            )
            .all()
        ):
            wrong_answers.setdefault(question_id, []).append(
                _normalize_choice_answer(kinds_by_id[question_id], given)
            )

    rows = []
    for question in questions:
        answered, correct = totals.get(question.id, (0, 0))
        flag = classify_question(question.difficulty, answered, correct)

        top_text, top_count = None, 0
        top = most_common_wrong_answer(wrong_answers.get(question.id, []))
        if top is not None:
            value, top_count = top
            if question.kind == "mcq" and isinstance(value, int) and question.choices and 0 <= value < len(question.choices):
                top_text = str(question.choices[value])
            elif question.kind == "true_false":
                top_text = "صحيح" if value is True else "خطأ" if value is False else None

        rows.append(
            {
                "question_id": question.id,
                "prompt_ar": question.prompt_ar,
                "kind": question.kind,
                "difficulty": question.difficulty,
                "answered": answered,
                "correct": correct,
                "success_rate": success_rate(answered, correct),
                "flag": flag,
                "flag_label_ar": FLAG_LABELS_AR[flag],
                "top_wrong_answer": top_text,
                "top_wrong_count": top_count if top_text else 0,
            }
        )
    return sort_for_review(rows)
