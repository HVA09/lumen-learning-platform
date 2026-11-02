"""
مسارات الفصول الدراسية: المعلّم ينشئ فصلًا فيحصل على رمز دعوة قصير، الطالب ينضم
بالرمز، والمعلّم يدير القائمة (يشوف تقدّم كل طالب إجماليًا، يفصل طالبًا، يجدّد الرمز).

فصل الطالب هو نطاق اختياري للواجبات ولوحة المتصدرين (راجع routers/assignments.py
وrouters/gamification.py) — بدون فصل، كل شي يبقى عامًا على مستوى المنصة كما كان.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_teacher
from app.models.class_section import ClassEnrollment, ClassSection
from app.models.topic_mastery import TopicMastery
from app.models.user import User, UserRole
from app.schemas.class_section import (
    ClassCreate,
    ClassDetailOut,
    ClassJoinRequest,
    ClassOut,
    StudentInClassOut,
)
from app.services.invite_codes import generate_invite_code, normalize_invite_code

router = APIRouter(prefix="/classes", tags=["Classes"])

INVITE_CODE_MAX_ATTEMPTS = 8


def _student_counts(db: Session, class_ids: list[int]) -> dict[int, int]:
    if not class_ids:
        return {}
    return dict(
        db.query(ClassEnrollment.class_section_id, func.count(ClassEnrollment.id))
        .filter(ClassEnrollment.class_section_id.in_(class_ids))
        .group_by(ClassEnrollment.class_section_id)
        .all()
    )


def _class_out(
    class_section: ClassSection,
    student_count: int,
    *,
    include_invite_code: bool = True,
) -> ClassOut:
    return ClassOut(
        id=class_section.id,
        name=class_section.name,
        invite_code=class_section.invite_code if include_invite_code else None,
        teacher_user_id=class_section.teacher_user_id,
        is_archived=class_section.is_archived,
        created_at=class_section.created_at,
        student_count=student_count,
    )


def _get_owned_class_or_404(class_id: int, user: User, db: Session) -> ClassSection:
    class_section = db.get(ClassSection, class_id)
    if not class_section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الفصل غير موجود")
    if class_section.teacher_user_id != user.id and user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="فقط معلّم الفصل يقدر يديره"
        )
    return class_section


@router.post("", response_model=ClassOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    for _ in range(INVITE_CODE_MAX_ATTEMPTS):
        class_section = ClassSection(
            name=payload.name.strip(),
            teacher_user_id=teacher.id,
            invite_code=generate_invite_code(),
        )
        db.add(class_section)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(class_section)
        return _class_out(class_section, student_count=0)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="تعذر توليد رمز دعوة فريد، حاول مرة ثانية"
    )


@router.get("", response_model=list[ClassOut], response_model_exclude_none=True)
def list_classes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == UserRole.admin:
        classes = db.query(ClassSection).order_by(ClassSection.created_at.desc()).all()
    elif current_user.role == UserRole.teacher:
        classes = (
            db.query(ClassSection)
            .filter(ClassSection.teacher_user_id == current_user.id)
            .order_by(ClassSection.created_at.desc())
            .all()
        )
    else:
        classes = (
            db.query(ClassSection)
            .join(ClassEnrollment, ClassEnrollment.class_section_id == ClassSection.id)
            .filter(ClassEnrollment.student_user_id == current_user.id)
            .order_by(ClassSection.created_at.desc())
            .all()
        )
    counts = _student_counts(db, [c.id for c in classes])
    include_invite_code = current_user.role in (UserRole.teacher, UserRole.admin)
    return [
        _class_out(c, counts.get(c.id, 0), include_invite_code=include_invite_code)
        for c in classes
    ]


@router.get("/{class_id}", response_model=ClassDetailOut)
def get_class(
    class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    """تفاصيل الفصل مع قائمة الطلاب ومتوسط إتقان كل واحد — لمعلّم الفصل أو admin فقط"""
    class_section = _get_owned_class_or_404(class_id, teacher, db)

    enrollments = (
        db.query(ClassEnrollment, User)
        .join(User, User.id == ClassEnrollment.student_user_id)
        .filter(ClassEnrollment.class_section_id == class_id)
        .order_by(ClassEnrollment.joined_at)
        .all()
    )
    student_ids = [u.id for _, u in enrollments]
    averages = {}
    if student_ids:
        averages = dict(
            db.query(TopicMastery.user_id, func.avg(TopicMastery.mastery_percentage))
            .filter(TopicMastery.user_id.in_(student_ids))
            .group_by(TopicMastery.user_id)
            .all()
        )

    students = [
        StudentInClassOut(
            user_id=user.id,
            email=user.email,
            display_name=user.full_name.strip() if user.full_name and user.full_name.strip() else user.email,
            joined_at=enrollment.joined_at,
            average_mastery=round(float(averages.get(user.id, 0.0)), 1),
        )
        for enrollment, user in enrollments
    ]
    return ClassDetailOut(**_class_out(class_section, len(students)).model_dump(), students=students)


@router.patch("/{class_id}", response_model=ClassOut)
def update_class(
    class_id: int,
    payload: ClassCreate,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    class_section = _get_owned_class_or_404(class_id, teacher, db)
    class_section.name = payload.name.strip()
    db.commit()
    db.refresh(class_section)
    counts = _student_counts(db, [class_id])
    return _class_out(class_section, counts.get(class_id, 0))


@router.post("/{class_id}/regenerate-code", response_model=ClassOut)
def regenerate_invite_code(
    class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    """يجدّد رمز الدعوة — مفيد لو تسرّب الرمز القديم لغير طلاب الفصل"""
    class_section = _get_owned_class_or_404(class_id, teacher, db)
    for _ in range(INVITE_CODE_MAX_ATTEMPTS):
        class_section.invite_code = generate_invite_code()
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        db.refresh(class_section)
        counts = _student_counts(db, [class_id])
        return _class_out(class_section, counts.get(class_id, 0))
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="تعذر توليد رمز دعوة فريد، حاول مرة ثانية"
    )


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int, teacher: User = Depends(require_teacher), db: Session = Depends(get_db)
):
    class_section = _get_owned_class_or_404(class_id, teacher, db)
    db.delete(class_section)
    db.commit()


@router.delete("/{class_id}/students/{student_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(
    class_id: int,
    student_user_id: int,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    _get_owned_class_or_404(class_id, teacher, db)
    enrollment = (
        db.query(ClassEnrollment)
        .filter(
            ClassEnrollment.class_section_id == class_id,
            ClassEnrollment.student_user_id == student_user_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="الطالب غير مسجّل بهذا الفصل")
    db.delete(enrollment)
    db.commit()


@router.post("/join", response_model=ClassOut, response_model_exclude_none=True)
def join_class(
    payload: ClassJoinRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    code = normalize_invite_code(payload.invite_code)
    class_section = db.query(ClassSection).filter(ClassSection.invite_code == code).first()
    if not class_section or class_section.is_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="رمز الدعوة غير صحيح")

    already_enrolled = (
        db.query(ClassEnrollment.id)
        .filter(
            ClassEnrollment.class_section_id == class_section.id,
            ClassEnrollment.student_user_id == current_user.id,
        )
        .first()
    )
    if not already_enrolled:
        db.add(ClassEnrollment(class_section_id=class_section.id, student_user_id=current_user.id))
        db.commit()

    counts = _student_counts(db, [class_section.id])
    return _class_out(class_section, counts.get(class_section.id, 0), include_invite_code=False)
