"""
الفصول الدراسية: يملكها معلّم (أو admin)، والطلاب ينضمّون برمز دعوة قصير.
تُستخدم لتحديد نطاق الواجبات ولوحة المتصدرين على مجموعة طلاب بدل كل المنصة.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ClassSection(Base):
    __tablename__ = "class_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    teacher_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    teacher = relationship("User")


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_section_id", "student_user_id", name="uq_enrollment_class_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_section_id: Mapped[int] = mapped_column(
        ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student = relationship("User")
