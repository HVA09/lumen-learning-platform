"""
بطاقات مراجعة جاهزة لكل موضوع — الطالب يضيفها لبطاقاته الشخصية بضغطة واحدة
فتدخل جدول التكرار المتباعد (review_cards) وتُجدول له تلقائيًا.
"""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TopicCard(Base):
    __tablename__ = "topic_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str | None] = mapped_column(String(60), unique=True, nullable=True)
    front_text: Mapped[str] = mapped_column(Text, nullable=False)
    back_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
