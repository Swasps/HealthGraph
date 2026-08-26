import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import Role


class User(TimestampMixin, Base):
    """Authentication identity. Deliberately separate from Patient/Provider:
    not every patient has a login, and the split keeps auth concerns
    (password, tokens) out of clinical tables."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    patient: Mapped["Patient | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False
    )
    provider: Mapped["Provider | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    """Refresh tokens are stored hashed (never the raw token) so a database
    leak doesn't hand out valid sessions. Rotation on use + explicit
    revocation lets us invalidate a stolen token without waiting for TTL."""

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_user_id_revoked", "user_id", "revoked"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
