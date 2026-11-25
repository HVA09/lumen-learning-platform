"""
محاولات الاختبار: يحتفظ الخادم بسياق الإنشاء وتعريفات الأسئلة والإجابات المسودة.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        Index("ix_quiz_attempts_user_topic", "user_id", "topic_id"),
        Index("ix_quiz_attempts_class_section_id", "class_section_id"),
        Index("ix_quiz_attempts_user_role_at_creation", "user_role_at_creation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("class_sections.id", ondelete="SET NULL"), nullable=True
    )
    # NULL is reserved for legacy attempts whose attempt-time role is unknown.
    user_role_at_creation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    question_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Write-once map keyed by question ID; contains the exact presented and grading definition.
    question_definition_snapshots: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Learner input only; never contains correctness, score, or grading output.
    draft_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Legacy open attempts without snapshots are expired rather than reinterpreted.
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Result per question after submission.
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    score_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
