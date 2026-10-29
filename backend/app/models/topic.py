from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    learning_outcomes_ar: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    skill_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prerequisite_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    simulation_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    subject = relationship("Subject", back_populates="topics")
    prerequisite = relationship("Topic", remote_side=[id])
