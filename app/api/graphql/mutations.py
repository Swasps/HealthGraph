"""GraphQL mutations.

Every write here passes through the same gates a read does — the
caller's role, and, for anything patient-scoped, `PatientAccessPolicy` —
plus whatever domain rule applies on top (a NURSE can record a vital
sign but not prescribe a medication). Every mutation is audited via
`AuditService`, which commits through its own connection so the audit
trail survives even if something later in the request rolls back.
"""

from datetime import UTC, datetime
from uuid import UUID

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.inputs import (
    AddAllergyInput,
    AddDiagnosisInput,
    AddPatientProviderRelationshipInput,
    CreateEncounterInput,
    CreatePatientInput,
    PrescribeMedicationInput,
    RecordLabResultInput,
    RecordVitalSignInput,
    UpdatePatientContactInfoInput,
)
from app.api.graphql.types.clinical import Allergy, Diagnosis, Encounter, Medication
from app.api.graphql.types.observations import LabResult, VitalSign
from app.api.graphql.types.patient import Patient
from app.api.graphql.types.relationship import PatientProviderRelationship
from app.core.errors import AuthorizationError, ConflictError, NotFoundError, ValidationError
from app.domain.current_user import CurrentUser
from app.domain.validators import require_date_order, require_non_empty, require_not_future
from app.models.enums import Role
from app.repositories.clinical import (
    AllergyRepository,
    DiagnosisRepository,
    EncounterRepository,
    MedicationRepository,
)
from app.repositories.observations import LabResultRepository, VitalSignRepository
from app.repositories.patient import PatientRepository
from app.repositories.provider import ProviderRepository
from app.repositories.relationship import PatientProviderRelationshipRepository
from app.services.audit_service import AuditService
from app.services.patient_service import PatientService

_CLINICAL_WRITE_ROLES = (Role.DOCTOR, Role.NURSE, Role.ADMIN)


def _require_role(user: CurrentUser, *roles: Role) -> None:
    if user.role not in roles:
        raise AuthorizationError("Your role does not permit this action.")


def _resolve_acting_provider_id(user: CurrentUser, requested: strawberry.ID | None) -> UUID:
    """A DOCTOR/NURSE always writes clinical records as themselves — an
    input field letting them attribute a write to another provider would
    be a privilege-escalation hole. Only ADMIN, acting on behalf of a
    provider, needs to name one explicitly."""
    if user.role is Role.ADMIN:
        if requested is None:
            raise ValidationError("providerId is required for admin-initiated writes.")
        return UUID(str(requested))
    if user.provider_id is None:
        raise AuthorizationError("Your account is not linked to a provider profile.")
    return user.provider_id


@strawberry.type
class Mutation:
    @strawberry.mutation(description="Create a new patient record. ADMIN only.")
    async def create_patient(
        self, info: strawberry.Info[GraphQLContext, None], input: CreatePatientInput
    ) -> Patient:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, Role.ADMIN)

        mrn = require_non_empty(input.mrn, "mrn")
        first_name = require_non_empty(input.first_name, "firstName")
        last_name = require_non_empty(input.last_name, "lastName")
        require_not_future(input.date_of_birth, "dateOfBirth")

        repo = PatientRepository(context.session)
        if await repo.get_by_mrn(mrn) is not None:
            raise ConflictError(f"A patient with MRN {mrn} already exists.")

        patient = repo.create(
            mrn=mrn,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=input.date_of_birth,
            sex=input.sex,
            phone=input.phone,
            email=input.email,
            address=input.address,
            ssn=input.ssn,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="patient.create",
            resource_type="patient",
            resource_id=str(patient.id),
        )
        return Patient.from_model(patient)

    @strawberry.mutation(
        description="Update a patient's contact info. ADMIN, or the patient themselves."
    )
    async def update_patient_contact_info(
        self,
        info: strawberry.Info[GraphQLContext, None],
        patient_id: strawberry.ID,
        input: UpdatePatientContactInfoInput,
    ) -> Patient:
        context = info.context
        user = context.require_authenticated()
        pid = UUID(str(patient_id))

        is_self = user.role is Role.PATIENT and user.patient_id == pid
        if user.role is not Role.ADMIN and not is_self:
            raise AuthorizationError("You may only update your own contact information.")

        repo = PatientRepository(context.session)
        patient = await repo.get_by_id(pid)
        if patient is None:
            raise NotFoundError(f"No patient with id {pid}.")

        if input.phone is not None:
            patient.phone = input.phone
        if input.email is not None:
            patient.email = input.email
        if input.address is not None:
            patient.address = input.address
        await context.session.commit()
        # `updated_at` is server-computed (onupdate=func.now()); after an
        # UPDATE it's left expired rather than eagerly re-fetched the way
        # a fresh INSERT's RETURNING clause populates it. Refreshing here,
        # inside the async context, avoids `from_model` below triggering
        # an implicit lazy-load attempt outside SQLAlchemy's greenlet
        # bridge — which raises `MissingGreenlet`, not just a stale value.
        await context.session.refresh(patient)

        # The patient's demographic record is cached (see PatientService)
        # — a stale phone number after this write would be a correctness
        # bug, not just a performance quirk, so invalidation is mandatory
        # here rather than left to TTL expiry.
        await PatientService(context.session, context.cache).invalidate(pid)

        await AuditService().record(
            user_id=user.user_id,
            action="patient.update_contact_info",
            resource_type="patient",
            resource_id=str(pid),
        )
        return Patient.from_model(patient)

    @strawberry.mutation(
        description=(
            "Establish a clinical relationship between a patient and a "
            "provider. ADMIN only — this is what grants a DOCTOR/NURSE "
            "access to a patient's record."
        )
    )
    async def add_patient_provider_relationship(
        self,
        info: strawberry.Info[GraphQLContext, None],
        input: AddPatientProviderRelationshipInput,
    ) -> PatientProviderRelationship:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, Role.ADMIN)

        patient_id = UUID(str(input.patient_id))
        provider_id = UUID(str(input.provider_id))
        start_date = input.start_date or datetime.now(UTC).date()

        repo = PatientProviderRelationshipRepository(context.session)
        relationship = repo.create(
            patient_id=patient_id,
            provider_id=provider_id,
            relationship_type=input.relationship_type,
            start_date=start_date,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="patient_provider_relationship.create",
            resource_type="patient_provider_relationship",
            resource_id=str(relationship.id),
            details={"patient_id": str(patient_id), "provider_id": str(provider_id)},
        )
        return PatientProviderRelationship.from_model(relationship)

    @strawberry.mutation(
        description="Record a clinical encounter. Requires an active relationship with the patient."
    )
    async def create_encounter(
        self, info: strawberry.Info[GraphQLContext, None], input: CreateEncounterInput
    ) -> Encounter:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, *_CLINICAL_WRITE_ROLES)

        patient_id = UUID(str(input.patient_id))
        await context.access_policy.require_full_record_access(user, patient_id)
        provider_id = _resolve_acting_provider_id(user, input.provider_id)

        provider = await ProviderRepository(context.session).get_by_id(provider_id)
        if provider is None:
            raise NotFoundError("Provider not found.")

        repo = EncounterRepository(context.session)
        encounter = repo.create(
            patient_id=patient_id,
            provider_id=provider_id,
            facility_id=provider.facility_id,
            encounter_type=input.encounter_type,
            chief_complaint=input.chief_complaint,
            started_at=input.started_at or datetime.now(UTC),
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="encounter.create",
            resource_type="encounter",
            resource_id=str(encounter.id),
        )
        return Encounter.from_model(encounter)

    @strawberry.mutation(description="Add a diagnosis to a patient's record.")
    async def add_diagnosis(
        self, info: strawberry.Info[GraphQLContext, None], input: AddDiagnosisInput
    ) -> Diagnosis:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, *_CLINICAL_WRITE_ROLES)

        patient_id = UUID(str(input.patient_id))
        await context.access_policy.require_full_record_access(user, patient_id)

        icd10_code = require_non_empty(input.icd10_code, "icd10Code")
        description = require_non_empty(input.description, "description")

        repo = DiagnosisRepository(context.session)
        diagnosis = repo.create(
            patient_id=patient_id,
            icd10_code=icd10_code,
            description=description,
            diagnosed_at=input.diagnosed_at or datetime.now(UTC),
            encounter_id=UUID(str(input.encounter_id)) if input.encounter_id else None,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="diagnosis.create",
            resource_type="diagnosis",
            resource_id=str(diagnosis.id),
        )
        return Diagnosis.from_model(diagnosis)

    @strawberry.mutation(
        description="Prescribe a medication. DOCTOR or ADMIN only — nurses cannot prescribe."
    )
    async def prescribe_medication(
        self, info: strawberry.Info[GraphQLContext, None], input: PrescribeMedicationInput
    ) -> Medication:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, Role.DOCTOR, Role.ADMIN)

        patient_id = UUID(str(input.patient_id))
        await context.access_policy.require_full_record_access(user, patient_id)
        provider_id = _resolve_acting_provider_id(user, input.provider_id)

        name = require_non_empty(input.name, "name")
        dosage = require_non_empty(input.dosage, "dosage")
        frequency = require_non_empty(input.frequency, "frequency")
        require_date_order(
            input.start_date, input.end_date, start_field="startDate", end_field="endDate"
        )

        repo = MedicationRepository(context.session)
        medication = repo.create(
            patient_id=patient_id,
            prescribed_by=provider_id,
            name=name,
            dosage=dosage,
            frequency=frequency,
            route=input.route,
            start_date=input.start_date,
            encounter_id=UUID(str(input.encounter_id)) if input.encounter_id else None,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="medication.prescribe",
            resource_type="medication",
            resource_id=str(medication.id),
        )
        return Medication.from_model(medication)

    @strawberry.mutation(description="Record a lab result. LAB_TECHNICIAN or ADMIN only.")
    async def record_lab_result(
        self, info: strawberry.Info[GraphQLContext, None], input: RecordLabResultInput
    ) -> LabResult:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, Role.LAB_TECHNICIAN, Role.ADMIN)

        # Lab technicians don't hold a clinical relationship with the
        # patient (see PatientAccessPolicy.can_view_lab_results) — the
        # role gate above is the whole check for this mutation.
        patient_id = UUID(str(input.patient_id))
        test_name = require_non_empty(input.test_name, "testName")
        test_code = require_non_empty(input.test_code, "testCode")
        value = require_non_empty(input.value, "value")

        repo = LabResultRepository(context.session)
        lab_result = repo.create(
            patient_id=patient_id,
            ordered_by=UUID(str(input.ordered_by_provider_id)),
            test_name=test_name,
            test_code=test_code,
            value=value,
            unit=input.unit,
            reference_range=input.reference_range,
            abnormal_flag=input.abnormal_flag,
            resulted_at=input.resulted_at or datetime.now(UTC),
            encounter_id=UUID(str(input.encounter_id)) if input.encounter_id else None,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="lab_result.record",
            resource_type="lab_result",
            resource_id=str(lab_result.id),
        )
        return LabResult.from_model(lab_result)

    @strawberry.mutation(description="Record a vital sign measurement.")
    async def record_vital_sign(
        self, info: strawberry.Info[GraphQLContext, None], input: RecordVitalSignInput
    ) -> VitalSign:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, *_CLINICAL_WRITE_ROLES)

        patient_id = UUID(str(input.patient_id))
        await context.access_policy.require_full_record_access(user, patient_id)
        unit = require_non_empty(input.unit, "unit")

        repo = VitalSignRepository(context.session)
        vital_sign = repo.create(
            patient_id=patient_id,
            vital_type=input.vital_type,
            value=input.value,
            unit=unit,
            recorded_at=input.recorded_at or datetime.now(UTC),
            encounter_id=UUID(str(input.encounter_id)) if input.encounter_id else None,
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="vital_sign.record",
            resource_type="vital_sign",
            resource_id=str(vital_sign.id),
        )
        return VitalSign.from_model(vital_sign)

    @strawberry.mutation(description="Record a known allergy or adverse reaction.")
    async def add_allergy(
        self, info: strawberry.Info[GraphQLContext, None], input: AddAllergyInput
    ) -> Allergy:
        context = info.context
        user = context.require_authenticated()
        _require_role(user, *_CLINICAL_WRITE_ROLES)

        patient_id = UUID(str(input.patient_id))
        await context.access_policy.require_full_record_access(user, patient_id)
        allergen = require_non_empty(input.allergen, "allergen")

        repo = AllergyRepository(context.session)
        allergy = repo.create(
            patient_id=patient_id,
            allergen=allergen,
            severity=input.severity,
            reaction=input.reaction,
            recorded_at=input.recorded_at or datetime.now(UTC),
        )
        await context.session.commit()

        await AuditService().record(
            user_id=user.user_id,
            action="allergy.create",
            resource_type="allergy",
            resource_id=str(allergy.id),
        )
        return Allergy.from_model(allergy)
