import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import Sex


class Patient(TimestampMixin, Base):
    """The subject of every clinical record. `mrn` (medical record number)
    is the natural identifier clinicians use day to day and is indexed for
    lookup by front-desk/admin flows; `id` is the surrogate key everything
    else joins against.

    `ssn` is intentionally nullable and never returned by default GraphQL
    field selection logic without an explicit authorization check — see
    the field-level resolver in app/api/graphql/types/patient.py.
    """

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    mrn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[Sex] = mapped_column(Enum(Sex, name="sex"), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    ssn: Mapped[str | None] = mapped_column(String(11))

    user: Mapped["User | None"] = relationship(back_populates="patient")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"Patient(id={self.id!r}, mrn={self.mrn!r})"
