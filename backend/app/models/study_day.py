"""
أيام الدراسة: صف واحد لكل (طالب، يوم UTC) فيه نشاط تعليمي فعلي — يُستخدم لحساب الـ streak
(أيام متتالية) بدون الحاجة لتخزين عدّاد قابل للتلاعب.
"""
from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudyDay(Base):
    __tablename__ = "study_days"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_study_day_user_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
