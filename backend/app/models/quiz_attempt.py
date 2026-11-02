"""
محاولات الاختبار: السيرفر هو اللي يختار الأسئلة ويصحّح — الطالب ما يرسل درجة أبدًا،
يرسل إجاباته فقط. mode: practice (تدريب) أو gateway (اختبار بوابة الإتقان).
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_quiz_attempts_user_topic", "user_id", "topic_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    question_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # نتيجة كل سؤال بعد التسليم: [{question_id, correct, given_answer}]
    results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    score_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
