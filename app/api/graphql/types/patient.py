from datetime import date, datetime
from uuid import UUID

import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.enums import Sex
from app.models.patient import Patient as PatientModel
from app.services.patient_service import PatientRecord


@strawberry.type(description="A patient and their demographic information.")
class Patient:
    id: strawberry.ID
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone: str | None
    email: str | None
    address: str | None
    created_at: datetime
    updated_at: datetime

    _ssn: strawberry.Private[str | None]

    @strawberry.field(
        description=(
            "Social Security Number. Field-level authorization: only visible "
            "to the platform admin or the patient themselves, even for a "
            "provider who otherwise has full access to this patient's record."
        )
    )
    def ssn(self, info: strawberry.Info[GraphQLContext, None]) -> str | None:
        context = info.context
        if context.current_user is None:
            return None
        if context.access_policy.can_view_ssn(context.current_user, UUID(str(self.id))):
            return self._ssn
        return None

    @classmethod
    def from_record(cls, record: PatientRecord) -> "Patient":
        """Builds from the cache-aside `PatientRecord` projection — used by
        the single-patient `patient(id)` query."""
        return cls(
            id=strawberry.ID(str(record.id)),
            mrn=record.mrn,
            first_name=record.first_name,
            last_name=record.last_name,
            date_of_birth=record.date_of_birth,
            sex=record.sex,
            phone=record.phone,
            email=record.email,
            address=record.address,
            created_at=record.created_at,
            updated_at=record.updated_at,
            _ssn=record.ssn,
        )

    @classmethod
    def from_model(cls, patient: PatientModel) -> "Patient":
        """Builds directly from the ORM row — used by list queries
        (`patients`), which go straight through the repository rather
        than the single-id cache (a search result set isn't cacheable by
        a single key the way `patient(id)` is)."""
        return cls(
            id=strawberry.ID(str(patient.id)),
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            sex=patient.sex,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            _ssn=patient.ssn,
        )
