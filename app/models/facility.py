import uuid

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import FacilityType


class Facility(TimestampMixin, Base):
    """A hospital, clinic, lab, or pharmacy. Encounters and providers are
    anchored to a facility so access policies can be scoped by location
    (e.g. a nurse assigned to one hospital) without a separate join table."""

    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facility_type: Mapped[FacilityType] = mapped_column(
        Enum(FacilityType, name="facility_type"), nullable=False
    )
    address: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20))

    providers: Mapped[list["Provider"]] = relationship(back_populates="facility")  # noqa: F821
