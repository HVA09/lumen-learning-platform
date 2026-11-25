"""
نتيجة كل سؤال مع نسخة التعريف الدقيقة التي عُرضت على المتعلم وقت المحاولة.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class QuestionResult(Base):
    __tablename__ = "question_results"
    __table_args__ = (
        Index("ix_question_results_question_id", "question_id"),
        Index("ix_question_results_definition_version", "question_id", "question_definition_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    given_answer: Mapped[Any] = mapped_column(JSON, nullable=True)
    # NULL for historical rows created before immutable definition snapshots existed.
    question_definition_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question_prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_kind_snapshot: Mapped[str | None] = mapped_column(String(20), nullable=True)
    question_difficulty_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_choices_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    question_correct_answer_snapshot: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    question_tolerance_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
