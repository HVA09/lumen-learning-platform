"""
تسجيل منصات LTI 1.3 (مثل Moodle/Canvas) وربط مستخدمي المنصة بحسابات Lumen المحلية
"""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class LTIPlatform(Base):
    """منصة LMS مسجّلة (Moodle/Canvas...) — تُنشأ يدويًا بعد تبادل معلومات التسجيل
    بين لوحة إدارة LMS ولوحة إدارة Lumen (خطوة تسجيل تُسوّى مرة وحدة لكل منصة)"""
    __tablename__ = "lti_platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)  # claim "iss"
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_login_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_token_url: Mapped[str] = mapped_column(String(500), nullable=False)
    jwks_url: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (UniqueConstraint("issuer", "client_id", name="uq_lti_platform_issuer_client"),)


class LTIUserLink(Base):
    """يربط (منصة + معرّف مستخدم LTI) بحساب Lumen محلي — يُنشأ تلقائيًا أول launch"""
    __tablename__ = "lti_user_links"
    __table_args__ = (
        UniqueConstraint("platform_id", "lti_subject", name="uq_lti_user_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False)
    lti_subject: Mapped[str] = mapped_column(String(255), nullable=False)  # claim "sub"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    platform = relationship("LTIPlatform")
    user = relationship("User")



class LTIAuthState(Base):
    """حالة OIDC عشوائية أحادية الاستخدام، مخزنة بهشّها فقط."""
    __tablename__ = "lti_auth_states"
    __table_args__ = (UniqueConstraint("state_hash", name="uq_lti_auth_states_state_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    platform_id: Mapped[int] = mapped_column(ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    target_link_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    platform = relationship("LTIPlatform")


class LTIAuthCode(Base):
    """رمز تبادل قصير العمر؛ لا يحمل JWT ولا يمكن استخدامه أكثر من مرة."""
    __tablename__ = "lti_auth_codes"
    __table_args__ = (UniqueConstraint("code_hash", name="uq_lti_auth_codes_code_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")


class LTIAssignmentLink(Base):
    """ربط واجب Lumen بعنصر مورد/تقييم واحد في منصة LTI."""
    __tablename__ = "lti_assignment_links"
    __table_args__ = (
        UniqueConstraint(
            "platform_id", "deployment_id", "resource_link_id",
            name="uq_lti_assignment_link_resource",
        ),
        CheckConstraint("score_maximum > 0", name="ck_lti_assignment_link_score_maximum"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_link_id: Mapped[str] = mapped_column(String(255), nullable=False)
    lineitem_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    score_scope_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    score_maximum: Mapped[float] = mapped_column(
        Float, default=100.0, server_default="100", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    platform = relationship("LTIPlatform")
    assignment = relationship("Assignment")

    @property
    def lineitem_ready(self) -> bool:
        return bool(self.lineitem_url and self.score_scope_allowed)


class LTIAGSGradeEvent(Base):
    """Transactional outbox for at-least-once LTI AGS score delivery."""
    __tablename__ = "lti_ags_grade_events"
    __table_args__ = (
        UniqueConstraint(
            "assignment_link_id", "submission_id", "grade_version",
            name="uq_lti_ags_grade_event_version",
        ),
        CheckConstraint(
            "score_given >= 0 AND score_given <= score_maximum",
            name="ck_lti_ags_grade_event_score_range",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'dead')",
            name="ck_lti_ags_grade_event_status",
        ),
        Index("ix_lti_ags_grade_events_due", "status", "next_attempt_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_link_id: Mapped[int] = mapped_column(
        ForeignKey("lti_assignment_links.id", ondelete="CASCADE"), nullable=False
    )
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("assignment_submissions.id", ondelete="CASCADE"), nullable=False
    )
    grade_version: Mapped[int] = mapped_column(Integer, nullable=False)
    lti_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    score_given: Mapped[float] = mapped_column(Float, nullable=False)
    score_maximum: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    assignment_link = relationship("LTIAssignmentLink")
    submission = relationship("AssignmentSubmission")
