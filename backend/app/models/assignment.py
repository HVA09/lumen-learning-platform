"""
الواجبات: ينشئها معلّم (أو admin)، ويسلّمها الطالب كإجابة مكتوبة، والمعلّم هو اللي يقيّمها
يدويًا بنسبة مئوية وملاحظات — rubric_criteria قائمة معايير يستخدمها المعلّم كقائمة تحقق عند التقييم.
"""
import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    graded = "graded"


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    class_section_id: Mapped[int | None] = mapped_column(
        ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # معايير التقييم بالعربي — قائمة نصوص يراها الطالب ويقيّم المعلّم على أساسها
    rubric_criteria: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    creator = relationship("User")
    topic = relationship("Topic")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_user_id", name="uq_submission_assignment_student"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    written_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    grade_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Set only when this submission is made in a verified matching LTI launch session.
    lti_assignment_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("lti_assignment_links.id", ondelete="SET NULL"), nullable=True
    )
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus), default=SubmissionStatus.pending, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignment = relationship("Assignment")
    lti_assignment_link = relationship("LTIAssignmentLink")
    student = relationship("User", foreign_keys=[student_user_id])
    grader = relationship("User", foreign_keys=[graded_by_user_id])
