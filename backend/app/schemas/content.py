from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.assessments.domain.quiz_logic import normalize_correct_answer, validate_question_definition


class QuestionCreate(BaseModel):
    kind: str
    prompt_ar: str = Field(min_length=1, max_length=2000)
    choices: list[str] | None = None
    correct_answer: Any
    tolerance: float | None = Field(default=None, ge=0)
    explanation_ar: str | None = Field(default=None, max_length=2000)
    difficulty: int = Field(default=1, ge=1, le=3)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_definition(self):
        errors = validate_question_definition(
            self.kind, self.choices, self.correct_answer, self.tolerance
        )
        if errors:
            raise ValueError("؛ ".join(errors))
        self.correct_answer = normalize_correct_answer(self.kind, self.correct_answer)
        if self.kind != "mcq":
            self.choices = None
        if self.kind != "numeric":
            self.tolerance = None
        return self


class QuestionAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic_id: int
    key: str | None
    kind: str
    prompt_ar: str
    choices: list[str] | None
    correct_answer: Any
    tolerance: float | None
    explanation_ar: str | None
    difficulty: int
    is_active: bool


class LessonCreate(BaseModel):
    title_ar: str = Field(min_length=1, max_length=255)
    body_md: str = Field(min_length=1, max_length=20000)
    estimated_minutes: int = Field(default=5, ge=1, le=240)
    order_index: int = Field(default=0, ge=0)
    is_published: bool = True


class LessonAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    topic_id: int
    slug: str
    title_ar: str
    body_md: str
    estimated_minutes: int
    order_index: int
    is_published: bool


class QuestionAnalyticsOut(BaseModel):
    """تحليل سؤال واحد: أداء الطلاب الفعلي مقابل الصعوبة المصنّفة"""
    question_id: int
    prompt_ar: str
    kind: str
    difficulty: int
    answered: int
    correct: int
    success_rate: float | None
    flag: str
    flag_label_ar: str
    top_wrong_answer: str | None = None  # أكثر إجابة خاطئة تكرارًا (لسؤال الاختيار من متعدد وصح/خطأ)
    top_wrong_count: int = 0
