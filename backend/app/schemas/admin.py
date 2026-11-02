from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import UserRole


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    event_type: str
    description: str
    created_at: datetime


class AdminStats(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_lessons: int
    total_questions: int
    total_quiz_attempts: int
    total_assignments: int
    total_submissions: int
    total_files: int
    storage_used_bytes: int


class DailyStatsPoint(BaseModel):
    date: str
    new_users: int
    quiz_attempts: int
    assignment_submissions: int
    average_quiz_score: float
