from datetime import datetime
from uuid import UUID

from app.models.observations import LabResult, VitalSign
from app.repositories.base import PatientScopedRepository


class LabResultRepository(PatientScopedRepository[LabResult]):
    model = LabResult
    patient_id_column = LabResult.patient_id
    sort_column = LabResult.resulted_at

    def create(
        self,
        *,
        patient_id: UUID,
        ordered_by: UUID,
        test_name: str,
        test_code: str,
        value: str,
        resulted_at: datetime,
        unit: str | None = None,
        reference_range: str | None = None,
        abnormal_flag=None,
        encounter_id: UUID | None = None,
    ) -> LabResult:
        from app.models.enums import AbnormalFlag

        lab_result = LabResult(
            patient_id=patient_id,
            encounter_id=encounter_id,
            ordered_by=ordered_by,
            test_name=test_name,
            test_code=test_code,
            value=value,
            unit=unit,
            reference_range=reference_range,
            abnormal_flag=abnormal_flag or AbnormalFlag.NORMAL,
            resulted_at=resulted_at,
        )
        return self.add(lab_result)


class VitalSignRepository(PatientScopedRepository[VitalSign]):
    model = VitalSign
    patient_id_column = VitalSign.patient_id
    sort_column = VitalSign.recorded_at

    def create(
        self,
        *,
        patient_id: UUID,
        vital_type,
        value: float,
        unit: str,
        recorded_at: datetime,
        encounter_id: UUID | None = None,
    ) -> VitalSign:
        vital_sign = VitalSign(
            patient_id=patient_id,
            encounter_id=encounter_id,
            vital_type=vital_type,
            value=value,
            unit=unit,
            recorded_at=recorded_at,
        )
        return self.add(vital_sign)
