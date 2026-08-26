from datetime import date, datetime

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.enums import AllergySeverity as AllergySeverityEnum
from app.api.graphql.enums import DiagnosisStatus, EncounterStatus, EncounterType
from app.api.graphql.enums import MedicationStatus as MedicationStatusEnum
from app.api.graphql.types.provider import Facility, Provider
from app.models.clinical import Allergy as AllergyModel
from app.models.clinical import Diagnosis as DiagnosisModel
from app.models.clinical import Encounter as EncounterModel
from app.models.clinical import Medication as MedicationModel
from app.models.clinical import Procedure as ProcedureModel


@strawberry.type(description="A single clinical visit.")
class Encounter:
    id: strawberry.ID
    encounter_type: EncounterType
    status: EncounterStatus
    chief_complaint: str | None
    notes: str | None
    started_at: datetime
    ended_at: datetime | None

    _provider_id: strawberry.Private[str]
    _facility_id: strawberry.Private[str]

    @strawberry.field(description="The provider who saw the patient during this encounter.")
    async def provider(self, info: strawberry.Info[GraphQLContext, None]) -> Provider:
        model = await info.context.loaders.providers_by_id.load(self._provider_id)
        return Provider.from_model(model)

    @strawberry.field(description="The facility where this encounter took place.")
    async def facility(self, info: strawberry.Info[GraphQLContext, None]) -> Facility:
        model = await info.context.loaders.facilities_by_id.load(self._facility_id)
        return Facility.from_model(model)

    @classmethod
    def from_model(cls, encounter: EncounterModel) -> "Encounter":
        return cls(
            id=strawberry.ID(str(encounter.id)),
            encounter_type=encounter.encounter_type,
            status=encounter.status,
            chief_complaint=encounter.chief_complaint,
            notes=encounter.notes,
            started_at=encounter.started_at,
            ended_at=encounter.ended_at,
            _provider_id=encounter.provider_id,
            _facility_id=encounter.facility_id,
        )


@strawberry.type(description="An ICD-10-coded diagnosis.")
class Diagnosis:
    id: strawberry.ID
    icd10_code: str
    description: str
    status: DiagnosisStatus
    diagnosed_at: datetime

    @classmethod
    def from_model(cls, diagnosis: DiagnosisModel) -> "Diagnosis":
        return cls(
            id=strawberry.ID(str(diagnosis.id)),
            icd10_code=diagnosis.icd10_code,
            description=diagnosis.description,
            status=diagnosis.status,
            diagnosed_at=diagnosis.diagnosed_at,
        )


@strawberry.type(description="A prescription.")
class Medication:
    id: strawberry.ID
    name: str
    dosage: str
    frequency: str
    route: str | None
    status: MedicationStatusEnum
    start_date: date
    end_date: date | None

    _prescribed_by: strawberry.Private[str]

    @strawberry.field(description="The provider who prescribed this medication.")
    async def prescribed_by(self, info: strawberry.Info[GraphQLContext, None]) -> Provider:
        model = await info.context.loaders.providers_by_id.load(self._prescribed_by)
        return Provider.from_model(model)

    @classmethod
    def from_model(cls, medication: MedicationModel) -> "Medication":
        return cls(
            id=strawberry.ID(str(medication.id)),
            name=medication.name,
            dosage=medication.dosage,
            frequency=medication.frequency,
            route=medication.route,
            status=medication.status,
            start_date=medication.start_date,
            end_date=medication.end_date,
            _prescribed_by=medication.prescribed_by,
        )


@strawberry.type(description="A known allergy or adverse reaction.")
class Allergy:
    id: strawberry.ID
    allergen: str
    reaction: str | None
    severity: AllergySeverityEnum
    recorded_at: datetime

    @classmethod
    def from_model(cls, allergy: AllergyModel) -> "Allergy":
        return cls(
            id=strawberry.ID(str(allergy.id)),
            allergen=allergy.allergen,
            reaction=allergy.reaction,
            severity=allergy.severity,
            recorded_at=allergy.recorded_at,
        )


@strawberry.type(description="A CPT-coded procedure.")
class Procedure:
    id: strawberry.ID
    cpt_code: str
    description: str
    performed_at: datetime

    _performed_by: strawberry.Private[str]

    @strawberry.field(description="The provider who performed this procedure.")
    async def performed_by(self, info: strawberry.Info[GraphQLContext, None]) -> Provider:
        model = await info.context.loaders.providers_by_id.load(self._performed_by)
        return Provider.from_model(model)

    @classmethod
    def from_model(cls, procedure: ProcedureModel) -> "Procedure":
        return cls(
            id=strawberry.ID(str(procedure.id)),
            cpt_code=procedure.cpt_code,
            description=procedure.description,
            performed_at=procedure.performed_at,
            _performed_by=procedure.performed_by,
        )
