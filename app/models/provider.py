import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Provider(TimestampMixin, Base):
    """A clinician (doctor, nurse, lab technician). Linked 1:1 to a User
    for login, and to a Facility for where they practice. `npi_number` is
    the real-world National Provider Identifier — unique, so it also acts
    as a natural dedupe key on import from an upstream system."""

    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    npi_number: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(150))

    user: Mapped["User | None"] = relationship(back_populates="provider")  # noqa: F821
    facility: Mapped["Facility"] = relationship(back_populates="providers")
