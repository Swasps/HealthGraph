import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin
from app.models.enums import AbnormalFlag, VitalSignType


class LabResult(TimestampMixin, Base):
    """A single lab test result. `test_code` follows LOINC convention.
    `abnormal_flag` is stored (not computed on read) because the reference
    range that produced it may itself change over time — we want to know
    what the lab actually flagged at result time."""

    __tablename__ = "lab_results"
    __table_args__ = (Index("ix_lab_results_patient_resulted", "patient_id", "resulted_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL")
    )
    ordered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    abnormal_flag: Mapped[AbnormalFlag] = mapped_column(
        Enum(AbnormalFlag, name="abnormal_flag"), default=AbnormalFlag.NORMAL, nullable=False
    )
    resulted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class VitalSign(TimestampMixin, Base):
    """A point-in-time vital sign measurement. Modeled as one row per
    reading (rather than wide columns for BP/HR/temp/...) so new vital
    types don't require a migration and the timeline can treat every
    reading uniformly regardless of type."""

    __tablename__ = "vital_signs"
    __table_args__ = (Index("ix_vital_signs_patient_recorded", "patient_id", "recorded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL")
    )
    vital_type: Mapped[VitalSignType] = mapped_column(
        Enum(VitalSignType, name="vital_sign_type"), nullable=False
    )
    value: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
