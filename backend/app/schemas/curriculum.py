from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TopicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name_ar: str
    name_en: str
    learning_outcomes_ar: list[str]
    skill_tags: list[str]
    prerequisite_topic_id: int | None
    simulation_type: str | None
    order_index: int


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name_ar: str
    name_en: str
    order_index: int


class SubjectWithTopicsOut(SubjectOut):
    topics: list[TopicOut]


class MasteryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    topic_id: int
    mastery_percentage: float
    gateway_quiz_passed: bool
    attempts_count: int
    last_practiced_at: datetime | None


class LessonOut(BaseModel):
    id: int
    topic_id: int
    slug: str
    title_ar: str
    body_md: str
    estimated_minutes: int
    order_index: int
    completed: bool = False


class UnlockedAchievementOut(BaseModel):
    key: str
    title_ar: str


class LessonCompleteOut(BaseModel):
    lesson_id: int
    completed: bool
    new_achievements: list[UnlockedAchievementOut]


class PathTopicOut(BaseModel):
    id: int
    slug: str
    name_ar: str
    name_en: str
    learning_outcomes_ar: list[str]
    simulation_type: str | None
    prerequisite_topic_id: int | None
    prerequisite_name_ar: str | None
    status: str  # locked | available | in_progress | mastered
    mastery_percentage: float
    gateway_quiz_passed: bool
    lessons_total: int
    lessons_completed: int
    questions_count: int


class PathSubjectOut(BaseModel):
    id: int
    slug: str
    name_ar: str
    name_en: str
    topics: list[PathTopicOut]


class LearningPathOut(BaseModel):
    subjects: list[PathSubjectOut]
    recommended_topic_id: int | None
    topics_total: int
    topics_mastered: int
    overall_mastery: float
