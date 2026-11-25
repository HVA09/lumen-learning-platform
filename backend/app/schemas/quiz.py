from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.curriculum import UnlockedAchievementOut

MAX_ANSWER_TEXT_LENGTH = 500
MAX_QUIZ_QUESTIONS = 50


class QuizStartRequest(BaseModel):
    mode: Literal["practice", "gateway"] = "practice"
    # model_fields_set distinguishes omission (resume existing context) from explicit null.
    class_section_id: int | None = None


class QuizQuestionOut(BaseModel):
    """السؤال كما يُعرض للطالب — بدون الإجابة الصحيحة أو الشرح."""
    id: int
    kind: str
    prompt_ar: str
    choices: list[str] | None
    difficulty: int


class QuizAttemptOut(BaseModel):
    attempt_id: int
    topic_id: int
    mode: str
    class_section_id: int | None = None
    pass_percentage: float | None
    resumed: bool
    saved_answers: dict[str, Any] = Field(default_factory=dict)
    questions: list[QuizQuestionOut]


class QuizAnswerIn(BaseModel):
    question_id: int
    answer: Any = None

    @field_validator("answer")
    @classmethod
    def answer_is_simple_value(cls, v: Any) -> Any:
        if v is None or isinstance(v, (bool, int, float)):
            return v
        if isinstance(v, str):
            if len(v) > MAX_ANSWER_TEXT_LENGTH:
                raise ValueError("الإجابة طويلة جدًا")
            return v
        raise ValueError("صيغة الإجابة غير مدعومة")


class QuizSubmitRequest(BaseModel):
    answers: list[QuizAnswerIn] = Field(default_factory=list, max_length=MAX_QUIZ_QUESTIONS)


class QuizDraftAnswersRequest(BaseModel):
    answers: list[QuizAnswerIn] = Field(default_factory=list, max_length=MAX_QUIZ_QUESTIONS)


class QuizDraftAnswersOut(BaseModel):
    saved_at: datetime
    answer_count: int


class QuizQuestionResultOut(BaseModel):
    question_id: int
    kind: str
    prompt_ar: str
    choices: list[str] | None
    correct: bool
    given_answer: Any
    correct_answer_text: str
    explanation_ar: str | None


class QuizResultOut(BaseModel):
    attempt_id: int
    topic_id: int
    mode: str
    score_percentage: float
    correct_count: int
    total: int
    passed: bool | None
    mastery_percentage: float
    gateway_quiz_passed: bool
    new_achievements: list[UnlockedAchievementOut]
    results: list[QuizQuestionResultOut]


class QuizHistoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mode: str
    score_percentage: float | None
    passed: bool | None
    submitted_at: datetime | None
