"""
مسارات الواجبات: المعلّم (أو admin) ينشئ الواجب، الطالب يسلّم إجابة مكتوبة، والمعلّم يقيّمها
يدويًا بنسبة مئوية وملاحظات. الطالب يشوف نتيجته وملاحظات معلّمه، ولا يقدر يعدّل تسليمًا تم تقييمه.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.audit import log_event
from app.database import get_db
from app.dependencies import get_current_user, require_teacher
from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
from app.models.lti import LTIAssignmentLink
from app.models.class_section import ClassEnrollment, ClassSection
from app.models.user import User, UserRole
from app.notifications import notify
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentListItem,
    AssignmentOut,
    SubmissionCreate,
    SubmissionDetailOut,
    SubmissionGrade,
    SubmissionOut,
)
from app.services.achievements import check_and_award_achievements
from app.services.study_activity import record_study_activity
from app.services.lti_service import create_lti_ags_grade_event

router = APIRouter(prefix="/assignments", tags=["Assignments"])


def _get_assignment_or_404(assignment_id: int, db: Session) -> Assignment:
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الواجب غير موجود")
    return assignment


def _can_manage(assignment: Assignment, user: User) -> bool:
    """منشئ الواجب أو admin"""
    return assignment.created_by_user_id == user.id or user.role == UserRole.admin


def _is_enrolled(db: Session, class_section_id: int, user_id: int) -> bool:
    return (
        db.query(ClassEnrollment.id)
        .filter(
            ClassEnrollment.class_section_id == class_section_id,
            ClassEnrollment.student_user_id == user_id,
        )
        .first()
        is not None
    )


def _ensure_assignment_visible(assignment: Assignment, user: User, db: Session) -> None:
    """واجب بلا فصل مرئي للكل؛ واجب بفصل محصور بمنشئه أو admin أو طلاب ذلك الفصل"""
    if assignment.class_section_id is None or _can_manage(assignment, user):
        return
    if not _is_enrolled(db, assignment.class_section_id, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الواجب غير موجود")


def _get_manageable_assignment(assignment_id: int, user: User, db: Session) -> Assignment:
    assignment = _get_assignment_or_404(assignment_id, db)
    if not _can_manage(assignment, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="فقط منشئ الواجب يقدر يدير تسليماته",
        )
    return assignment


def _detail(submission: AssignmentSubmission, student: User) -> SubmissionDetailOut:
    return SubmissionDetailOut(
        **SubmissionOut.model_validate(submission).model_dump(),
        student_name=student.full_name or student.email,
    )


@router.post("", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    if payload.class_section_id is not None:
        class_section = db.get(ClassSection, payload.class_section_id)
        if not class_section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفصل غير موجود")
        if class_section.teacher_user_id != teacher.id and teacher.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="ما تقدر تنشئ واجبًا لفصل غير فصلك"
            )

    assignment = Assignment(
        created_by_user_id=teacher.id,
        topic_id=payload.topic_id,
        class_section_id=payload.class_section_id,
        title=payload.title,
        description=payload.description,
        rubric_criteria=[c.strip() for c in payload.rubric_criteria if c.strip()],
        due_at=payload.due_at,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("", response_model=list[AssignmentListItem])
def list_assignments(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """الواجبات المرئية للمستخدم: العامة (بدون فصل) + واجبات فصوله (منشئها له، أو مسجَّل فيها كطالب)
    — بجانب كل واجب حالة تسليم الطالب الحالي، وللمعلّم منشئ الواجب أعداد التسليمات"""
    query = db.query(Assignment)
    if current_user.role != UserRole.admin:
        visible_class_ids = [
            row[0]
            for row in db.query(ClassEnrollment.class_section_id)
            .filter(ClassEnrollment.student_user_id == current_user.id)
            .all()
        ]
        visibility_conditions = [
            Assignment.class_section_id.is_(None),
            Assignment.created_by_user_id == current_user.id,
        ]
        if visible_class_ids:
            visibility_conditions.append(Assignment.class_section_id.in_(visible_class_ids))
        query = query.filter(or_(*visibility_conditions))
    assignments = query.order_by(Assignment.created_at.desc()).all()
    if not assignments:
        return []
    assignment_ids = [a.id for a in assignments]

    my_submissions = {
        s.assignment_id: s
        for s in db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.student_user_id == current_user.id,
            AssignmentSubmission.assignment_id.in_(assignment_ids),
        )
        .all()
    }

    submissions_count: dict[int, int] = {}
    pending_count: dict[int, int] = {}
    if current_user.role in (UserRole.teacher, UserRole.admin):
        submissions_count = dict(
            db.query(AssignmentSubmission.assignment_id, func.count(AssignmentSubmission.id))
            .filter(AssignmentSubmission.assignment_id.in_(assignment_ids))
            .group_by(AssignmentSubmission.assignment_id)
            .all()
        )
        pending_count = dict(
            db.query(AssignmentSubmission.assignment_id, func.count(AssignmentSubmission.id))
            .filter(
                AssignmentSubmission.assignment_id.in_(assignment_ids),
                AssignmentSubmission.status == SubmissionStatus.submitted,
            )
            .group_by(AssignmentSubmission.assignment_id)
            .all()
        )

    items = []
    for assignment in assignments:
        mine = my_submissions.get(assignment.id)
        manages = _can_manage(assignment, current_user)
        items.append(
            AssignmentListItem(
                **AssignmentOut.model_validate(assignment).model_dump(),
                can_manage=manages,
                my_status=mine.status if mine else None,
                my_grade_percentage=mine.grade_percentage if mine else None,
                submissions_count=submissions_count.get(assignment.id, 0) if manages else None,
                pending_grading_count=pending_count.get(assignment.id, 0) if manages else None,
            )
        )
    return items


@router.get("/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(assignment_id, db)
    _ensure_assignment_visible(assignment, current_user, db)
    return assignment


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = _get_manageable_assignment(assignment_id, current_user, db)
    log_event(
        db, "assignment_deleted", f"{current_user.email} حذف الواجب #{assignment_id}", current_user.id
    )
    db.delete(assignment)
    db.commit()


@router.get("/{assignment_id}/my-submission", response_model=SubmissionOut | None)
def get_my_submission(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_assignment_visible(_get_assignment_or_404(assignment_id, db), current_user, db)
    return (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_user_id == current_user.id,
        )
        .first()
    )


@router.post("/{assignment_id}/submit", response_model=SubmissionOut)
def submit_assignment(
    assignment_id: int,
    payload: SubmissionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = _get_assignment_or_404(assignment_id, db)
    if (
        assignment.class_section_id is not None
        and not _can_manage(assignment, current_user)
        and not _is_enrolled(db, assignment.class_section_id, current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="هذا الواجب مخصص لطلاب فصل معيّن لست مسجَّلًا فيه"
        )

    submission = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_user_id == current_user.id,
        )
        .first()
    )
    if submission and submission.status == SubmissionStatus.graded:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="تم تقييم هذا الواجب — ما يمكن تعديل التسليم بعد التقييم",
        )

    is_first_submission = submission is None
    if is_first_submission:
        submission = AssignmentSubmission(assignment_id=assignment_id, student_user_id=current_user.id)
        db.add(submission)

    now = datetime.now(timezone.utc)
    due_at = assignment.due_at
    if due_at is not None and due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    # Bind only to a mapping matching the verified LTI context on this exact browser session.
    # Normal Lumen sessions, unrelated assignments, and unmapped resources never fan out.
    auth_session = getattr(request.state, "auth_session", None)
    mapping = None
    if (
        auth_session is not None
        and auth_session.lti_platform_id is not None
        and auth_session.lti_deployment_id
        and auth_session.lti_resource_link_id
    ):
        mapping = db.query(LTIAssignmentLink).filter(
            LTIAssignmentLink.platform_id == auth_session.lti_platform_id,
            LTIAssignmentLink.deployment_id == auth_session.lti_deployment_id,
            LTIAssignmentLink.resource_link_id == auth_session.lti_resource_link_id,
            LTIAssignmentLink.assignment_id == assignment.id,
        ).first()
    submission.lti_assignment_link_id = mapping.id if mapping is not None else None

    submission.written_answer = payload.written_answer
    submission.status = SubmissionStatus.submitted
    submission.submitted_at = now
    submission.is_late = bool(due_at and now > due_at)
    db.commit()
    db.refresh(submission)

    record_study_activity(db, current_user.id)
    if is_first_submission:
        notify(
            db,
            assignment.created_by_user_id,
            "تسليم جديد",
            f'{current_user.full_name or current_user.email} سلّم واجب "{assignment.title}"',
            "assignment",
        )
    return submission


@router.get("/{assignment_id}/submissions", response_model=list[SubmissionDetailOut])
def list_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_manageable_assignment(assignment_id, current_user, db)
    rows = (
        db.query(AssignmentSubmission, User)
        .join(User, User.id == AssignmentSubmission.student_user_id)
        .filter(AssignmentSubmission.assignment_id == assignment_id)
        .order_by(AssignmentSubmission.submitted_at)
        .all()
    )
    return [_detail(submission, student) for submission, student in rows]


@router.post(
    "/{assignment_id}/submissions/{submission_id}/grade", response_model=SubmissionDetailOut
)
def grade_submission(
    assignment_id: int,
    submission_id: int,
    payload: SubmissionGrade,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    assignment = _get_manageable_assignment(assignment_id, teacher, db)
    submission = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.id == submission_id,
            AssignmentSubmission.assignment_id == assignment_id,
        )
        .with_for_update()
        .first()
    )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="التسليم غير موجود")
    if submission.status == SubmissionStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="الطالب لم يسلّم إجابته بعد"
        )

    submission.grade_percentage = payload.grade_percentage
    submission.feedback = (payload.feedback or "").strip() or None
    submission.graded_by_user_id = teacher.id
    submission.graded_at = datetime.now(timezone.utc)
    submission.status = SubmissionStatus.graded
    submission.grade_version = (submission.grade_version or 0) + 1
    create_lti_ags_grade_event(db, assignment, submission)
    db.commit()
    db.refresh(submission)

    student = db.get(User, submission.student_user_id)
    notify(
        db,
        submission.student_user_id,
        "تم تقييم واجبك",
        f'واجب "{assignment.title}" — النتيجة: {submission.grade_percentage:.0f}%',
        "assignment",
    )
    check_and_award_achievements(db, submission.student_user_id)
    return _detail(submission, student)
