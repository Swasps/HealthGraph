from datetime import date, datetime

import strawberry

from app.api.graphql.enums import AbnormalFlag as AbnormalFlagEnum
from app.api.graphql.enums import (
    AllergySeverity,
    EncounterType,
    RelationshipType,
    Sex,
    VitalSignType,
)


@strawberry.input
class CreatePatientInput:
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    ssn: str | None = None


@strawberry.input
class UpdatePatientContactInfoInput:
    phone: str | None = None
    email: str | None = None
    address: str | None = None


@strawberry.input
class AddPatientProviderRelationshipInput:
    patient_id: strawberry.ID
    provider_id: strawberry.ID
    relationship_type: RelationshipType
    start_date: date | None = None


@strawberry.input
class CreateEncounterInput:
    patient_id: strawberry.ID
    encounter_type: EncounterType
    chief_complaint: str | None = None
    started_at: datetime | None = None
    # Only honored for ADMIN callers; DOCTOR/NURSE always write as
    # themselves, whatever this is set to.
    provider_id: strawberry.ID | None = None


@strawberry.input
class AddDiagnosisInput:
    patient_id: strawberry.ID
    icd10_code: str
    description: str
    diagnosed_at: datetime | None = None
    encounter_id: strawberry.ID | None = None


@strawberry.input
class PrescribeMedicationInput:
    patient_id: strawberry.ID
    name: str
    dosage: str
    frequency: str
    start_date: date
    route: str | None = None
    end_date: date | None = None
    encounter_id: strawberry.ID | None = None
    provider_id: strawberry.ID | None = None


@strawberry.input
class RecordLabResultInput:
    patient_id: strawberry.ID
    ordered_by_provider_id: strawberry.ID
    test_name: str
    test_code: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    abnormal_flag: AbnormalFlagEnum | None = None
    resulted_at: datetime | None = None
    encounter_id: strawberry.ID | None = None


@strawberry.input
class RecordVitalSignInput:
    patient_id: strawberry.ID
    vital_type: VitalSignType
    value: float
    unit: str
    recorded_at: datetime | None = None
    encounter_id: strawberry.ID | None = None


@strawberry.input
class AddAllergyInput:
    patient_id: strawberry.ID
    allergen: str
    severity: AllergySeverity
    reaction: str | None = None
    recorded_at: datetime | None = None
