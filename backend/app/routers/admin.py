"""
مسارات لوحة الإدارة — Authorization بحسب الدور (role-based)، admin فقط
"""
import csv
import io
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import log_event
from app.cache import cache_delete, cache_get, cache_set
from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import require_admin
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.audit_log import AuditLog
from app.models.file_attachment import FileAttachment
from app.models.lesson import Lesson
from app.models.question import Question
from app.models.quiz_attempt import QuizAttempt
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminStats,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    DailyStatsPoint,
)

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=AdminStats)
def get_stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    cache_key = "admin:stats"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    stats = AdminStats(
        total_users=db.query(func.count(User.id)).scalar(),
        total_students=db.query(func.count(User.id)).filter(User.role == UserRole.user).scalar(),
        total_teachers=db.query(func.count(User.id)).filter(User.role == UserRole.teacher).scalar(),
        total_lessons=db.query(func.count(Lesson.id)).scalar(),
        total_questions=db.query(func.count(Question.id)).scalar(),
        total_quiz_attempts=db.query(func.count(QuizAttempt.id))
        .filter(QuizAttempt.submitted_at.is_not(None))
        .scalar(),
        total_assignments=db.query(func.count(Assignment.id)).scalar(),
        total_submissions=db.query(func.count(AssignmentSubmission.id)).scalar(),
        total_files=db.query(func.count(FileAttachment.id)).scalar(),
        storage_used_bytes=db.query(func.coalesce(func.sum(FileAttachment.size_bytes), 0)).scalar(),
    )
    result = stats.model_dump()
    cache_set(cache_key, result, app_settings.CACHE_TTL_SECONDS)
    return result


def _compute_daily_stats(db: Session, days: int) -> list[DailyStatsPoint]:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    def _by_day(rows) -> dict:
        return {row[0].date(): row[1:] for row in rows}

    users_rows = (
        db.query(func.date_trunc("day", User.created_at), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date_trunc("day", User.created_at))
        .all()
    )
    quiz_rows = (
        db.query(
            func.date_trunc("day", QuizAttempt.submitted_at),
            func.count(QuizAttempt.id),
            func.coalesce(func.avg(QuizAttempt.score_percentage), 0),
        )
        .filter(QuizAttempt.submitted_at.is_not(None), QuizAttempt.submitted_at >= since)
        .group_by(func.date_trunc("day", QuizAttempt.submitted_at))
        .all()
    )
    submission_rows = (
        db.query(
            func.date_trunc("day", AssignmentSubmission.submitted_at),
            func.count(AssignmentSubmission.id),
        )
        .filter(
            AssignmentSubmission.submitted_at.is_not(None),
            AssignmentSubmission.submitted_at >= since,
        )
        .group_by(func.date_trunc("day", AssignmentSubmission.submitted_at))
        .all()
    )

    users_map = _by_day(users_rows)
    quiz_map = _by_day(quiz_rows)
    submissions_map = _by_day(submission_rows)

    points = []
    today = datetime.now(timezone.utc).date()
    for offset in range(days, -1, -1):
        day = today - timedelta(days=offset)
        quiz_attempts, average_score = quiz_map.get(day, (0, 0))
        points.append(
            DailyStatsPoint(
                date=day.isoformat(),
                new_users=(users_map.get(day, (0,)))[0],
                quiz_attempts=quiz_attempts,
                assignment_submissions=(submissions_map.get(day, (0,)))[0],
                average_quiz_score=round(float(average_score or 0), 1),
            )
        )
    return points


@router.get("/analytics/daily", response_model=list[DailyStatsPoint])
def get_daily_analytics(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _compute_daily_stats(db, days)


@router.get("/analytics/export.csv", include_in_schema=False)
def export_analytics_csv(
    days: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    points = _compute_daily_stats(db, days)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["date", "new_users", "quiz_attempts", "assignment_submissions", "average_quiz_score"]
    )
    for p in points:
        writer.writerow(
            [p.date, p.new_users, p.quiz_attempts, p.assignment_submissions, p.average_quiz_score]
        )
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(User).order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    )


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود")

    data = payload.model_dump(exclude_unset=True)
    # منع الـ admin من تغيير دور حسابه أو تعطيله بنفسه — يقفل على نفسه ويخلّي النظام بدون admin
    if user.id == admin.id and (
        ("role" in data and data["role"] != user.role) or data.get("is_active") is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ما تقدر تغيّر دور حسابك أو تعطّله بنفسك",
        )
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    cache_delete("admin:stats")
    log_event(
        db, "admin_user_updated", f"admin {admin.email} عدّل المستخدم {user.email}: {data}", admin.id
    )
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ما تقدر تحذف حسابك من هنا — استخدم حذف الحساب من صفحتك الشخصية",
        )
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="المستخدم غير موجود")

    log_event(db, "admin_user_deleted", f"admin {admin.email} حذف المستخدم {user.email}", admin.id)
    db.delete(user)
    db.commit()
    cache_delete("admin:stats")


@router.get("/logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    )
