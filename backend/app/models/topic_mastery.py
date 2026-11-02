from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class TopicMastery(Base):
    __tablename__ = "topic_mastery"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_topic_mastery_user_topic"),
        Index("ix_topic_mastery_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    mastery_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    gateway_quiz_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempts_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_practiced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    topic = relationship("Topic")
