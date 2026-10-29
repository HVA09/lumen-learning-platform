"""
تسجيل منصات LTI 1.3 (مثل Moodle/Canvas) وربط مستخدمي المنصة بحسابات Lumen المحلية
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
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
