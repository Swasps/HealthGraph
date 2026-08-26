import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import RelationshipType


class PatientProviderRelationship(TimestampMixin, Base):
    """The authorization backbone of the system: a provider may only read
    or write a patient's records while an active relationship row exists
    between them. This table is checked by the access-policy layer on
    every patient-scoped query, not just enforced at the UI/API-gateway
    level, so it can't be bypassed by calling GraphQL directly.
    """

    __tablename__ = "patient_provider_relationships"
    __table_args__ = (
        UniqueConstraint(
            "patient_id", "provider_id", "relationship_type", name="uq_patient_provider_type"
        ),
        Index("ix_ppr_provider_active", "provider_id", "active"),
        Index("ix_ppr_patient_active", "patient_id", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType, name="relationship_type"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    patient: Mapped["Patient"] = relationship()  # noqa: F821
    provider: Mapped["Provider"] = relationship()  # noqa: F821
