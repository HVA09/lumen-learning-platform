from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    invite_code: str | None = None
    teacher_user_id: int
    is_archived: bool
    created_at: datetime
    student_count: int = 0


class StudentInClassOut(BaseModel):
    user_id: int
    email: EmailStr
    display_name: str
    joined_at: datetime
    average_mastery: float = 0.0


class ClassDetailOut(ClassOut):
    students: list[StudentInClassOut] = Field(default_factory=list)


class ClassJoinRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=20)
