"""
نتيجة كل سؤال بكل محاولة اختبار مُسلَّمة — صف مستقل لكل سؤال (بدل قراءة JSON
المحاولة كل مرة)، يخلّي تحليل الأسئلة (نسبة النجاح لكل سؤال) استعلام SQL بسيط.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class QuestionResult(Base):
    __tablename__ = "question_results"
    __table_args__ = (Index("ix_question_results_question_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    given_answer: Mapped[Any] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
