from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.assignment import SubmissionStatus


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10000)
    topic_id: int | None = None
    class_section_id: int | None = None
    rubric_criteria: list[str] = Field(default_factory=list, max_length=20)
    due_at: datetime | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_by_user_id: int
    topic_id: int | None
    class_section_id: int | None
    title: str
    description: str
    rubric_criteria: list[str]
    due_at: datetime | None
    created_at: datetime


class AssignmentListItem(AssignmentOut):
    """عنصر قائمة الواجبات: حالة تسليم الطالب الحالي + (للمعلّم منشئ الواجب) أعداد التسليمات"""
    my_status: SubmissionStatus | None = None
    my_grade_percentage: float | None = None
    submissions_count: int | None = None
    pending_grading_count: int | None = None


class SubmissionCreate(BaseModel):
    written_answer: str = Field(min_length=1, max_length=20000)

    @field_validator("written_answer")
    @classmethod
    def answer_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("الإجابة لا يمكن أن تكون فارغة")
        return v


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    assignment_id: int
    student_user_id: int
    written_answer: str | None
    is_late: bool
    grade_percentage: float | None
    feedback: str | None
    status: SubmissionStatus
    submitted_at: datetime | None
    graded_at: datetime | None


class SubmissionDetailOut(SubmissionOut):
    """نسخة المعلّم من التسليم — تضيف اسم الطالب"""
    student_name: str


class SubmissionGrade(BaseModel):
    grade_percentage: float = Field(ge=0, le=100)
    feedback: str | None = Field(default=None, max_length=5000)
