from uuid import UUID

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.types.patient import PatientType
from app.services.patient_service import PatientService


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
    ) -> PatientType | None:
        context = info.context
        current_user = context.require_authenticated()
        patient_id = UUID(str(id))

        await context.access_policy.require_full_record_access(current_user, patient_id)

        record = await PatientService(context.session, context.cache).get_patient(patient_id)
        if record is None:
            return None
        return PatientType.from_record(record)
