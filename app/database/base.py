from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model, so Alembic's autogenerate
    can discover the full schema from a single metadata object."""


class TimestampMixin:
    """created_at/updated_at columns, set by the database rather than the
    application clock so they stay correct regardless of app-server time
    skew or bulk/manual SQL writes."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
