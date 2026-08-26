from uuid import UUID

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.types.clinical import Encounter, Medication
from app.api.graphql.types.observations import LabResult
from app.api.graphql.types.pagination import Connection, to_connection
from app.api.graphql.types.patient import Patient
from app.models.enums import Role
from app.repositories.clinical import EncounterRepository, MedicationRepository
from app.repositories.observations import LabResultRepository
from app.repositories.pagination import Page
from app.repositories.patient import PatientRepository
from app.repositories.relationship import PatientProviderRelationshipRepository
from app.services.patient_service import PatientService

_MAX_PAGE_SIZE = 100


def _clamp(first: int) -> int:
    return min(max(first, 1), _MAX_PAGE_SIZE)


@strawberry.type
class Query:
    @strawberry.field(
        description=(
            "Fetch a single patient by id. Requires an active clinical "
            "relationship for DOCTOR/NURSE callers, ownership for PATIENT "
            "callers, or the ADMIN role — see the access policy."
        )
    )
    async def patient(
        self, info: strawberry.Info[GraphQLContext, None], id: strawberry.ID
    ) -> Patient | None:
        context = info.context
        current_user = context.require_authenticated()
        patient_id = UUID(str(id))

        await context.access_policy.require_full_record_access(current_user, patient_id)

        record = await PatientService(context.session, context.cache).get_patient(patient_id)
        if record is None:
            return None
        return Patient.from_record(record)

    @strawberry.field(
        description=(
            "Search patients by name, cursor-paginated. Results are scoped to "
            "the caller: ADMIN sees everyone, PATIENT sees only themselves, "
            "and DOCTOR/NURSE see only patients they have an active clinical "
            "relationship with."
        )
    )
    async def patients(
        self,
        info: strawberry.Info[GraphQLContext, None],
        name: str | None = None,
        first: int = 20,
        after: str | None = None,
    ) -> Connection[Patient]:
        context = info.context
        user = context.require_authenticated()
        first = _clamp(first)
        repo = PatientRepository(context.session)

        if user.role is Role.ADMIN:
            page = await repo.search(name=name, first=first, after=after)
        elif user.role is Role.PATIENT:
            ids = {user.patient_id} if user.patient_id else set()
            page = await repo.search_within(ids, name=name, first=first, after=after)
        elif user.role in (Role.DOCTOR, Role.NURSE) and user.provider_id is not None:
            relationships = PatientProviderRelationshipRepository(context.session)
            accessible_ids = await relationships.accessible_patient_ids(
                provider_id=user.provider_id
            )
            page = await repo.search_within(accessible_ids, name=name, first=first, after=after)
        else:
            page = Page.empty()

        return to_connection(page, Patient.from_model)

    @strawberry.field(
        description="An individual patient's encounters, most recent first, cursor-paginated."
    )
    async def patient_encounters(
        self,
        info: strawberry.Info[GraphQLContext, None],
        patient_id: strawberry.ID,
        first: int = 20,
        after: str | None = None,
    ) -> Connection[Encounter]:
        context = info.context
        user = context.require_authenticated()
        pid = UUID(str(patient_id))
        await context.access_policy.require_full_record_access(user, pid)

        repo = EncounterRepository(context.session)
        page = await repo.paginate_by_patient(pid, _clamp(first), after)
        return to_connection(page, Encounter.from_model)

    @strawberry.field(
        description="An individual patient's medications, most recent first, cursor-paginated."
    )
    async def patient_medications(
        self,
        info: strawberry.Info[GraphQLContext, None],
        patient_id: strawberry.ID,
        first: int = 20,
        after: str | None = None,
    ) -> Connection[Medication]:
        context = info.context
        user = context.require_authenticated()
        pid = UUID(str(patient_id))
        await context.access_policy.require_full_record_access(user, pid)

        repo = MedicationRepository(context.session)
        page = await repo.paginate_by_patient(pid, _clamp(first), after)
        return to_connection(page, Medication.from_model)

    @strawberry.field(
        description=(
            "An individual patient's lab results, most recent first, "
            "cursor-paginated. LAB_TECHNICIAN callers can read this even "
            "without a clinical relationship to the patient."
        )
    )
    async def patient_lab_results(
        self,
        info: strawberry.Info[GraphQLContext, None],
        patient_id: strawberry.ID,
        first: int = 20,
        after: str | None = None,
    ) -> Connection[LabResult]:
        context = info.context
        user = context.require_authenticated()
        pid = UUID(str(patient_id))
        await context.access_policy.require_lab_result_access(user, pid)

        repo = LabResultRepository(context.session)
        page = await repo.paginate_by_patient(pid, _clamp(first), after)
        return to_connection(page, LabResult.from_model)
