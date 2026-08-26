from datetime import date, datetime
from uuid import UUID

from app.models.clinical import Allergy, Diagnosis, Encounter, Medication, Procedure
from app.repositories.base import PatientScopedRepository


class EncounterRepository(PatientScopedRepository[Encounter]):
    model = Encounter
    patient_id_column = Encounter.patient_id
    sort_column = Encounter.started_at

    def create(
        self,
        *,
        patient_id: UUID,
        provider_id: UUID,
        facility_id: UUID,
        encounter_type,
        chief_complaint: str | None,
        started_at: datetime,
    ) -> Encounter:
        encounter = Encounter(
            patient_id=patient_id,
            provider_id=provider_id,
            facility_id=facility_id,
            encounter_type=encounter_type,
            chief_complaint=chief_complaint,
            started_at=started_at,
        )
        return self.add(encounter)


class DiagnosisRepository(PatientScopedRepository[Diagnosis]):
    model = Diagnosis
    patient_id_column = Diagnosis.patient_id
    sort_column = Diagnosis.diagnosed_at

    def create(
        self,
        *,
        patient_id: UUID,
        icd10_code: str,
        description: str,
        diagnosed_at: datetime,
        encounter_id: UUID | None = None,
    ) -> Diagnosis:
        diagnosis = Diagnosis(
            patient_id=patient_id,
            encounter_id=encounter_id,
            icd10_code=icd10_code,
            description=description,
            diagnosed_at=diagnosed_at,
        )
        return self.add(diagnosis)


class MedicationRepository(PatientScopedRepository[Medication]):
    model = Medication
    patient_id_column = Medication.patient_id
    sort_column = Medication.start_date
    sort_parser = staticmethod(date.fromisoformat)

    def create(
        self,
        *,
        patient_id: UUID,
        prescribed_by: UUID,
        name: str,
        dosage: str,
        frequency: str,
        start_date: date,
        route: str | None = None,
        encounter_id: UUID | None = None,
    ) -> Medication:
        medication = Medication(
            patient_id=patient_id,
            prescribed_by=prescribed_by,
            encounter_id=encounter_id,
            name=name,
            dosage=dosage,
            frequency=frequency,
            route=route,
            start_date=start_date,
        )
        return self.add(medication)


class AllergyRepository(PatientScopedRepository[Allergy]):
    model = Allergy
    patient_id_column = Allergy.patient_id
    sort_column = Allergy.recorded_at

    def create(
        self,
        *,
        patient_id: UUID,
        allergen: str,
        severity,
        recorded_at: datetime,
        reaction: str | None = None,
    ) -> Allergy:
        allergy = Allergy(
            patient_id=patient_id,
            allergen=allergen,
            severity=severity,
            reaction=reaction,
            recorded_at=recorded_at,
        )
        return self.add(allergy)


class ProcedureRepository(PatientScopedRepository[Procedure]):
    model = Procedure
    patient_id_column = Procedure.patient_id
    sort_column = Procedure.performed_at
