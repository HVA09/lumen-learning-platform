"""
مسارات الاختبارات: بدء محاولة (تدريب أو اختبار بوابة)، تسليم الإجابات، وسجل المحاولات.

كل التصحيح وحساب الإتقان يصير هنا بالسيرفر:
- الأسئلة تُرسل للطالب بدون الإجابات الصحيحة
- التسليم يستقبل الإجابات فقط، والسيرفر يحسب الدرجة ويحدّث إتقان الموضوع
- اجتياز اختبار البوابة (80% فأكثر) هو الطريقة الوحيدة لفتح المواضيع اللي تعتمد على هذا الموضوع
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.question import Question
from app.models.question_result import QuestionResult
from app.models.quiz_attempt import QuizAttempt
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.user import User, UserRole
from app.schemas.curriculum import UnlockedAchievementOut
from app.schemas.quiz import (
    QuizAttemptOut,
    QuizHistoryItemOut,
    QuizQuestionOut,
    QuizQuestionResultOut,
    QuizResultOut,
    QuizStartRequest,
    QuizSubmitRequest,
)
from app.services.achievements import check_and_award_achievements
from app.services.quiz_logic import (
    GATEWAY_PASS_PERCENTAGE,
    can_resume_attempt,
    compute_score_percentage,
    describe_correct_answer,
    gateway_cooldown_remaining_minutes,
    grade_answer,
    is_gateway_pass,
    public_choices,
    question_count_for_mode,
    select_question_ids,
    update_mastery,
)
from app.services.study_activity import record_study_activity

router = APIRouter(prefix="/quiz", tags=["Quiz"])

HISTORY_LIMIT = 10


def _ensure_topic_unlocked(topic: Topic, user: User, db: Session) -> None:
    """الموضوع اللي له متطلّب سابق يحتاج اجتياز اختبار بوابة المتطلّب أولًا (المعلّم وadmin مستثنون)"""
    if topic.prerequisite_topic_id is None or user.role in (UserRole.teacher, UserRole.admin):
        return
    prerequisite_passed = (
        db.query(TopicMastery.id)
        .filter(
            TopicMastery.user_id == user.id,
            TopicMastery.topic_id == topic.prerequisite_topic_id,
            TopicMastery.gateway_quiz_passed.is_(True),
        )
        .first()
    )
    if not prerequisite_passed:
        prerequisite = db.get(Topic, topic.prerequisite_topic_id)
        name = prerequisite.name_ar if prerequisite else "الموضوع السابق"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"اجتز اختبار بوابة «{name}» أولًا لفتح هذا الموضوع",
        )


def _load_questions(db: Session, question_ids: list[int]) -> list[Question]:
    """يجيب الأسئلة الفعّالة بنفس ترتيب المحاولة (الأسئلة المحذوفة أو المعطّلة تُتجاهل)"""
    if not question_ids:
        return []
    by_id = {
        q.id: q
        for q in db.query(Question)
        .filter(Question.id.in_(question_ids), Question.is_active.is_(True))
        .all()
    }
    return [by_id[qid] for qid in question_ids if qid in by_id]


def _attempt_out(attempt: QuizAttempt, questions: list[Question], resumed: bool) -> QuizAttemptOut:
    return QuizAttemptOut(
        attempt_id=attempt.id,
        topic_id=attempt.topic_id,
        mode=attempt.mode,
        pass_percentage=GATEWAY_PASS_PERCENTAGE if attempt.mode == "gateway" else None,
        resumed=resumed,
        questions=[
            QuizQuestionOut(
                id=q.id,
                kind=q.kind,
                prompt_ar=q.prompt_ar,
                choices=public_choices(q.kind, q.choices),
                difficulty=q.difficulty,
            )
            for q in questions
        ],
    )


@router.post("/topics/{topic_id}/start", response_model=QuizAttemptOut)
def start_quiz(
    topic_id: int,
    payload: QuizStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الموضوع غير موجود")
    _ensure_topic_unlocked(topic, current_user, db)

    now = datetime.now(timezone.utc)

    # محاولة سابقة غير مسلَّمة وحديثة → نعيدها (يحمي من فقدان التقدّم بتحديث الصفحة،
    # ويمنع تكرار طلب أسئلة جديدة لين تطلع أسئلة أسهل)
    open_attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.topic_id == topic_id,
            QuizAttempt.mode == payload.mode,
            QuizAttempt.submitted_at.is_(None),
        )
        .order_by(QuizAttempt.created_at.desc())
        .first()
    )
    if open_attempt and can_resume_attempt(open_attempt.created_at, now):
        questions = _load_questions(db, open_attempt.question_ids)
        if questions:
            return _attempt_out(open_attempt, questions, resumed=True)

    if payload.mode == "gateway":
        last_failed = (
            db.query(QuizAttempt.submitted_at)
            .filter(
                QuizAttempt.user_id == current_user.id,
                QuizAttempt.topic_id == topic_id,
                QuizAttempt.mode == "gateway",
                QuizAttempt.passed.is_(False),
            )
            .order_by(QuizAttempt.submitted_at.desc())
            .first()
        )
        remaining = gateway_cooldown_remaining_minutes(last_failed[0] if last_failed else None, now)
        if remaining > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"راجع الدرس أولًا ثم أعد اختبار البوابة بعد {remaining} دقيقة",
            )

    available_ids = [
        row[0]
        for row in db.query(Question.id)
        .filter(Question.topic_id == topic_id, Question.is_active.is_(True))
        .all()
    ]
    if not available_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="لا توجد أسئلة لهذا الموضوع بعد"
        )

    chosen_ids = select_question_ids(available_ids, question_count_for_mode(payload.mode))
    attempt = QuizAttempt(
        user_id=current_user.id, topic_id=topic_id, mode=payload.mode, question_ids=chosen_ids
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _attempt_out(attempt, _load_questions(db, chosen_ids), resumed=False)


@router.post("/attempts/{attempt_id}/submit", response_model=QuizResultOut)
def submit_quiz(
    attempt_id: int,
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المحاولة غير موجودة")
    if attempt.submitted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="هذه المحاولة سُلِّمت من قبل")

    questions = _load_questions(db, attempt.question_ids)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="أسئلة هذه المحاولة لم تعد متاحة — ابدأ محاولة جديدة"
        )

    given_by_question = {a.question_id: a.answer for a in payload.answers}
    results = []
    flags = []
    for question in questions:
        given = given_by_question.get(question.id)
        correct = grade_answer(question.kind, question.correct_answer, given, question.tolerance)
        flags.append(correct)
        results.append({"question_id": question.id, "correct": correct, "given_answer": given})

    score = compute_score_percentage(flags)
    passed = is_gateway_pass(score) if attempt.mode == "gateway" else None
    now = datetime.now(timezone.utc)

    mastery = (
        db.query(TopicMastery)
        .filter(TopicMastery.user_id == current_user.id, TopicMastery.topic_id == attempt.topic_id)
        .first()
    )
    if not mastery:
        mastery = TopicMastery(
            user_id=current_user.id,
            topic_id=attempt.topic_id,
            mastery_percentage=0.0,
            gateway_quiz_passed=False,
            attempts_count=0,
        )
        db.add(mastery)

    mastery.mastery_percentage = update_mastery(
        mastery.mastery_percentage, mastery.attempts_count, score, passed_gateway=bool(passed)
    )
    if passed:
        mastery.gateway_quiz_passed = True
    mastery.attempts_count += 1
    mastery.last_practiced_at = now

    attempt.results = results
    attempt.score_percentage = score
    attempt.passed = passed
    attempt.submitted_at = now
    # صف مستقل لكل سؤال — أساس تحليل الأسئلة للمعلّم (نسبة النجاح لكل سؤال بـ SQL مباشر)
    for result in results:
        db.add(
            QuestionResult(
                quiz_attempt_id=attempt.id,
                question_id=result["question_id"],
                correct=result["correct"],
                given_answer=result["given_answer"],
            )
        )
    db.commit()

    record_study_activity(db, current_user.id)
    unlocked = check_and_award_achievements(db, current_user.id)

    return QuizResultOut(
        attempt_id=attempt.id,
        topic_id=attempt.topic_id,
        mode=attempt.mode,
        score_percentage=score,
        correct_count=sum(1 for c in flags if c),
        total=len(flags),
        passed=passed,
        mastery_percentage=mastery.mastery_percentage,
        gateway_quiz_passed=mastery.gateway_quiz_passed,
        new_achievements=[UnlockedAchievementOut(key=a.key, title_ar=a.title_ar) for a in unlocked],
        results=[
            QuizQuestionResultOut(
                question_id=q.id,
                kind=q.kind,
                prompt_ar=q.prompt_ar,
                choices=public_choices(q.kind, q.choices),
                correct=result["correct"],
                given_answer=result["given_answer"],
                correct_answer_text=describe_correct_answer(
                    q.kind, q.correct_answer, q.choices, q.tolerance
                ),
                explanation_ar=q.explanation_ar,
            )
            for q, result in zip(questions, results)
        ],
    )


@router.get("/topics/{topic_id}/history", response_model=list[QuizHistoryItemOut])
def get_quiz_history(
    topic_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.topic_id == topic_id,
            QuizAttempt.submitted_at.is_not(None),
        )
        .order_by(QuizAttempt.submitted_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
