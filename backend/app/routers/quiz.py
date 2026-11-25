"""
مسارات الاختبارات: تعريفات الأسئلة ولقطات السياق محفوظة وقت بدء المحاولة،
والإجابات المسودة منفصلة عن التصحيح النهائي.
"""
import hashlib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.class_section import ClassEnrollment, ClassSection
from app.models.question import Question
from app.models.question_result import QuestionResult
from app.models.quiz_attempt import QuizAttempt
from app.models.topic import Topic
from app.models.topic_mastery import TopicMastery
from app.models.user import User, UserRole
from app.schemas.curriculum import UnlockedAchievementOut
from app.schemas.quiz import (
    QuizAttemptOut,
    QuizDraftAnswersOut,
    QuizDraftAnswersRequest,
    QuizHistoryItemOut,
    QuizQuestionOut,
    QuizQuestionResultOut,
    QuizResultOut,
    QuizStartRequest,
    QuizSubmitRequest,
)
from app.services.achievements import check_and_award_achievements
from app.modules.assessments.domain.quiz_logic import (
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


def _definition_snapshot(question: Question) -> dict:
    definition = {
        "kind": question.kind,
        "prompt_ar": question.prompt_ar,
        "difficulty": question.difficulty,
        "choices": question.choices,
        "correct_answer": question.correct_answer,
        "tolerance": question.tolerance,
        "explanation_ar": question.explanation_ar,
    }
    fingerprint_fields = {
        key: definition[key]
        for key in ("kind", "prompt_ar", "difficulty", "choices", "correct_answer", "tolerance")
    }
    canonical = json.dumps(
        fingerprint_fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    definition["question_definition_version"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return definition


def _snapshot_is_complete(attempt: QuizAttempt) -> bool:
    snapshots = attempt.question_definition_snapshots
    if not isinstance(snapshots, dict):
        return False
    return all(str(question_id) in snapshots for question_id in attempt.question_ids)


def _attempt_out(attempt: QuizAttempt, resumed: bool) -> QuizAttemptOut:
    snapshots = attempt.question_definition_snapshots or {}
    questions = []
    for question_id in attempt.question_ids:
        definition = snapshots[str(question_id)]
        questions.append(
            QuizQuestionOut(
                id=question_id,
                kind=definition["kind"],
                prompt_ar=definition["prompt_ar"],
                choices=public_choices(definition["kind"], definition.get("choices")),
                difficulty=definition["difficulty"],
            )
        )
    return QuizAttemptOut(
        attempt_id=attempt.id,
        topic_id=attempt.topic_id,
        mode=attempt.mode,
        class_section_id=attempt.class_section_id,
        pass_percentage=GATEWAY_PASS_PERCENTAGE if attempt.mode == "gateway" else None,
        resumed=resumed,
        saved_answers=attempt.draft_answers or {},
        questions=questions,
    )


def _answers_by_question(answers, attempt: QuizAttempt) -> dict[int, object]:
    allowed = {int(question_id) for question_id in attempt.question_ids}
    answer_map: dict[int, object] = {}
    for item in answers:
        if item.question_id not in allowed:
            raise HTTPException(status_code=422, detail="تتضمن الإجابات سؤالًا لا ينتمي إلى هذه المحاولة")
        if item.question_id in answer_map:
            raise HTTPException(status_code=422, detail="لا يمكن إرسال إجابة مكررة للسؤال نفسه")
        answer_map[item.question_id] = item.answer
    return answer_map


def _validate_attempt_owner(attempt_id: int, user: User, db: Session) -> QuizAttempt:
    attempt = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == user.id)
        .with_for_update()
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="المحاولة غير موجودة")
    if attempt.submitted_at is not None or attempt.expired_at is not None:
        raise HTTPException(status_code=409, detail="هذه المحاولة غير قابلة للتعديل")
    if not _snapshot_is_complete(attempt):
        raise HTTPException(status_code=409, detail="تعريفات أسئلة هذه المحاولة غير متاحة — ابدأ محاولة جديدة")
    return attempt


@router.post("/topics/{topic_id}/start", response_model=QuizAttemptOut)
def start_quiz(
    topic_id: int,
    payload: QuizStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="الموضوع غير موجود")
    _ensure_topic_unlocked(topic, current_user, db)

    requested_context = "class_section_id" in payload.model_fields_set
    requested_class_id = payload.class_section_id
    if requested_class_id is not None:
        if current_user.role != UserRole.user:
            raise HTTPException(status_code=403, detail="لا يمكن إسناد محاولة الموظف إلى فصل طالب")
        section = db.get(ClassSection, requested_class_id)
        enrolled = (
            db.query(ClassEnrollment.id)
            .filter(
                ClassEnrollment.class_section_id == requested_class_id,
                ClassEnrollment.student_user_id == current_user.id,
            )
            .first()
        )
        if not section or section.is_archived or not enrolled:
            raise HTTPException(status_code=403, detail="الفصل غير متاح أو أنك غير مسجل فيه")

    now = datetime.now(timezone.utc)
    open_attempt = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.topic_id == topic_id,
            QuizAttempt.mode == payload.mode,
            QuizAttempt.submitted_at.is_(None),
            QuizAttempt.expired_at.is_(None),
        )
        .order_by(QuizAttempt.created_at.desc())
        .first()
    )
    if open_attempt:
        if not can_resume_attempt(open_attempt.created_at, now):
            open_attempt.expired_at = now
            db.commit()
        elif not _snapshot_is_complete(open_attempt):
            # Legacy open attempts cannot be safely rebound to mutable current questions.
            open_attempt.expired_at = now
            db.commit()
        else:
            if requested_context and requested_class_id != open_attempt.class_section_id:
                raise HTTPException(status_code=409, detail="لا يمكن تغيير سياق الفصل لمحاولة بدأت بالفعل")
            return _attempt_out(open_attempt, resumed=True)

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
                status_code=429,
                detail=f"راجع الدرس أولًا ثم أعد اختبار البوابة بعد {remaining} دقيقة",
            )

    selected_questions = (
        db.query(Question)
        .filter(Question.topic_id == topic_id, Question.is_active.is_(True))
        .all()
    )
    available_ids = [question.id for question in selected_questions]
    if not available_ids:
        raise HTTPException(status_code=409, detail="لا توجد أسئلة لهذا الموضوع بعد")

    chosen_ids = select_question_ids(available_ids, question_count_for_mode(payload.mode))
    by_id = {question.id: question for question in selected_questions}
    snapshots = {str(question_id): _definition_snapshot(by_id[question_id]) for question_id in chosen_ids}
    attempt = QuizAttempt(
        user_id=current_user.id,
        topic_id=topic_id,
        mode=payload.mode,
        class_section_id=requested_class_id,
        user_role_at_creation=current_user.role.value,
        question_ids=chosen_ids,
        question_definition_snapshots=snapshots,
        draft_answers={},
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _attempt_out(attempt, resumed=False)


@router.put("/attempts/{attempt_id}/answers", response_model=QuizDraftAnswersOut)
def save_quiz_draft_answers(
    attempt_id: int,
    payload: QuizDraftAnswersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = _validate_attempt_owner(attempt_id, current_user, db)
    answer_map = _answers_by_question(payload.answers, attempt)
    attempt.draft_answers = {str(question_id): answer for question_id, answer in answer_map.items()}
    saved_at = datetime.now(timezone.utc)
    db.commit()
    return QuizDraftAnswersOut(saved_at=saved_at, answer_count=len(answer_map))


@router.post("/attempts/{attempt_id}/submit", response_model=QuizResultOut)
def submit_quiz(
    attempt_id: int,
    payload: QuizSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = _validate_attempt_owner(attempt_id, current_user, db)
    given_by_question = _answers_by_question(payload.answers, attempt)
    snapshots = attempt.question_definition_snapshots
    results = []
    flags = []
    question_rows = []
    for question_id in attempt.question_ids:
        definition = snapshots[str(question_id)]
        given = given_by_question.get(question_id)
        correct = grade_answer(
            definition["kind"],
            definition["correct_answer"],
            given,
            definition.get("tolerance"),
        )
        flags.append(correct)
        result = {
            "question_id": question_id,
            "correct": correct,
            "given_answer": given,
            "question_definition_version": definition["question_definition_version"],
        }
        results.append(result)
        question_rows.append((definition, result))

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
    attempt.draft_answers = None

    for question_id, (definition, result) in zip(attempt.question_ids, question_rows):
        db.add(
            QuestionResult(
                quiz_attempt_id=attempt.id,
                question_id=question_id,
                correct=result["correct"],
                given_answer=result["given_answer"],
                question_definition_version=definition["question_definition_version"],
                question_prompt_snapshot=definition["prompt_ar"],
                question_kind_snapshot=definition["kind"],
                question_difficulty_snapshot=definition["difficulty"],
                question_choices_snapshot=definition.get("choices"),
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
        correct_count=sum(1 for value in flags if value),
        total=len(flags),
        passed=passed,
        mastery_percentage=mastery.mastery_percentage,
        gateway_quiz_passed=mastery.gateway_quiz_passed,
        new_achievements=[UnlockedAchievementOut(key=item.key, title_ar=item.title_ar) for item in unlocked],
        results=[
            QuizQuestionResultOut(
                question_id=question_id,
                kind=definition["kind"],
                prompt_ar=definition["prompt_ar"],
                choices=public_choices(definition["kind"], definition.get("choices")),
                correct=result["correct"],
                given_answer=result["given_answer"],
                correct_answer_text=describe_correct_answer(
                    definition["kind"],
                    definition["correct_answer"],
                    definition.get("choices"),
                    definition.get("tolerance"),
                ),
                explanation_ar=definition.get("explanation_ar"),
            )
            for question_id, (definition, result) in zip(attempt.question_ids, question_rows)
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
