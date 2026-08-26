import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import (
    AllergySeverity,
    DiagnosisStatus,
    EncounterStatus,
    EncounterType,
    MedicationStatus,
)


class Encounter(TimestampMixin, Base):
    """A single clinical visit. This is the anchor most other clinical
    records optionally hang off of (`encounter_id`), and the timeline
    query's primary sort is built around `started_at`."""

    __tablename__ = "encounters"
    __table_args__ = (Index("ix_encounters_patient_started", "patient_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    encounter_type: Mapped[EncounterType] = mapped_column(
        Enum(EncounterType, name="encounter_type"), nullable=False
    )
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus, name="encounter_status"),
        default=EncounterStatus.SCHEDULED,
        nullable=False,
    )
    chief_complaint: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="encounter")
    medications: Mapped[list["Medication"]] = relationship(back_populates="encounter")
    procedures: Mapped[list["Procedure"]] = relationship(back_populates="encounter")


class Diagnosis(TimestampMixin, Base):
    """An ICD-10-coded diagnosis, optionally tied to the encounter where it
    was made. `status` distinguishes a one-off finding from a chronic
    condition that should keep showing up in the patient's active list."""

    __tablename__ = "diagnoses"
    __table_args__ = (Index("ix_diagnoses_patient_diagnosed", "patient_id", "diagnosed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL")
    )
    icd10_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DiagnosisStatus] = mapped_column(
        Enum(DiagnosisStatus, name="diagnosis_status"),
        default=DiagnosisStatus.ACTIVE,
        nullable=False,
    )
    diagnosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    encounter: Mapped["Encounter | None"] = relationship(back_populates="diagnoses")


class Medication(TimestampMixin, Base):
    """A prescription. `prescribed_by` is kept even when `encounter_id` is
    null so refills/standing prescriptions issued outside a visit still
    attribute responsibility to a provider."""

    __tablename__ = "medications"
    __table_args__ = (Index("ix_medications_patient_start", "patient_id", "start_date"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL")
    )
    prescribed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[MedicationStatus] = mapped_column(
        Enum(MedicationStatus, name="medication_status"),
        default=MedicationStatus.ACTIVE,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)

    encounter: Mapped["Encounter | None"] = relationship(back_populates="medications")


class Allergy(TimestampMixin, Base):
    """Allergies are not tied to an encounter — they're a standing patient
    attribute recorded whenever discovered, and are read far more often
    than they're written (every prescription flow should check them)."""

    __tablename__ = "allergies"
    __table_args__ = (Index("ix_allergies_patient_recorded", "patient_id", "recorded_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    allergen: Mapped[str] = mapped_column(String(255), nullable=False)
    reaction: Mapped[str | None] = mapped_column(String(500))
    severity: Mapped[AllergySeverity] = mapped_column(
        Enum(AllergySeverity, name="allergy_severity"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Procedure(TimestampMixin, Base):
    """A CPT-coded procedure performed during (or as) an encounter."""

    __tablename__ = "procedures"
    __table_args__ = (Index("ix_procedures_patient_performed", "patient_id", "performed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("encounters.id", ondelete="SET NULL")
    )
    performed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT"), nullable=False
    )
    cpt_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    encounter: Mapped["Encounter | None"] = relationship(back_populates="procedures")
