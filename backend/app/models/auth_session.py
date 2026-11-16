"""Server-side browser sessions for refresh-token rotation and revocation."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    # Random opaque session identifier embedded only in signed JWT claims.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Store only a SHA-256 digest of the current refresh JWT identifier.
    refresh_jti_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Verified LTI launch context is scoped to this browser/device session.
    lti_platform_id: Mapped[int | None] = mapped_column(ForeignKey("lti_platforms.id", ondelete="SET NULL"), nullable=True)
    lti_deployment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lti_resource_link_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Exact verified LMS subject associated with this browser launch.
    lti_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
