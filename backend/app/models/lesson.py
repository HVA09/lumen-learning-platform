"""
الدروس: محتوى شرح مكتوب لكل موضوع (Markdown) — هذا بديل شرح المعلّم الآلي السابق،
يكتبه ويراجعه معلّم حقيقي. LessonProgress يسجّل أي دروس أنهاها الطالب.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("topic_id", "slug", name="uq_lesson_topic_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topic = relationship("Topic")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
