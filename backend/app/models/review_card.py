"""
بطاقات التكرار المتباعد (Spaced Repetition, SM-2+) — كل بطاقة تتبع حالتها
الخاصة (new/learning/review/relearning) ومعامل السهولة الخاص فيها
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.modules.review.domain.sm2 import CardState


class ReviewCard(Base):
    __tablename__ = "review_cards"
    __table_args__ = (Index("ix_review_cards_user_due", "user_id", "due_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)

    front_text: Mapped[str] = mapped_column(Text, nullable=False)
    back_text: Mapped[str] = mapped_column(Text, nullable=False)

    state: Mapped[CardState] = mapped_column(Enum(CardState), default=CardState.new, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_leech: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    topic = relationship("Topic")
