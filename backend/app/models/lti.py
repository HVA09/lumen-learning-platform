"""
تسجيل منصات LTI 1.3 وربط مستخدمي المنصة بحسابات Lumen المحلية.
تُخزَّن حالات OIDC ورموز التبادل مجزّأة وتُستهلك مرة واحدة فقط.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class LTIPlatform(Base):
    """منصة LMS مسجّلة (Moodle/Canvas...)"""
    __tablename__ = "lti_platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    client_id: Mapped[str] = mapped_column(String(255), nullable=False)
    deployment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_login_url: Mapped[str] = mapped_column(String(500), nullable=False)
    auth_token_url: Mapped[str] = mapped_column(String(500), nullable=False)
    jwks_url: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (UniqueConstraint("issuer", "client_id", name="uq_lti_platform_issuer_client"),)


class LTIUserLink(Base):
    """يربط (منصة + معرّف مستخدم LTI) بحساب Lumen محلي"""
    __tablename__ = "lti_user_links"
    __table_args__ = (
        UniqueConstraint("platform_id", "lti_subject", name="uq_lti_user_link"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False)
    lti_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    platform = relationship("LTIPlatform")
    user = relationship("User")


class LTILoginState(Base):
    """حالة OIDC قصيرة العمر؛ state_hash لا يكشف قيمة state الأصلية."""
    __tablename__ = "lti_login_states"
    __table_args__ = (Index("ix_lti_login_states_expires_at", "expires_at"),)

    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("lti_platforms.id", ondelete="CASCADE"), nullable=False
    )
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    target_link_uri: Mapped[str] = mapped_column(String(1000), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LTIAuthCode(Base):
    """رمز تبادل مؤقت أحادي الاستخدام؛ تُحفظ بصمته فقط في قاعدة البيانات."""
    __tablename__ = "lti_auth_codes"
    __table_args__ = (
        Index("ix_lti_auth_codes_expires_at", "expires_at"),
        Index("ix_lti_auth_codes_user_id", "user_id"),
    )

    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
