"""Patient-data access policy.

This is the piece that keeps role-based access control from being a
rubber stamp: holding the DOCTOR role does not, by itself, grant access
to any patient. Every patient-scoped read is checked against this policy,
which in turn checks the `PatientProviderRelationship` table — so a
doctor with no relationship to a patient is refused exactly like an
unauthenticated caller would be, whether they go through GraphQL or REST.
"""

from uuid import UUID

from app.core.errors import AuthorizationError
from app.domain.current_user import CurrentUser
from app.models.enums import Role
from app.repositories.relationship import PatientProviderRelationshipRepository

_CLINICAL_ROLES = {Role.DOCTOR, Role.NURSE}


class PatientAccessPolicy:
    def __init__(self, relationship_repo: PatientProviderRelationshipRepository) -> None:
        self._relationships = relationship_repo

    async def can_view_full_record(self, user: CurrentUser, patient_id: UUID) -> bool:
        """Governs `patient`, `patientEncounters`, `patientMedications`,
        `patientTimeline` — anything covering the broad clinical picture,
        not just an isolated lab value."""
        if user.role is Role.ADMIN:
            return True
        if user.role is Role.PATIENT:
            return user.patient_id == patient_id
        if user.role in _CLINICAL_ROLES and user.provider_id is not None:
            return await self._relationships.has_active_relationship(
                patient_id=patient_id, provider_id=user.provider_id
            )
        return False

    async def can_view_lab_results(self, user: CurrentUser, patient_id: UUID) -> bool:
        """Lab technicians process orders system-wide and never hold a
        `PatientProviderRelationship` — that table models clinical care,
        not lab processing — so they get a narrower, unconditional grant
        here rather than inheriting `can_view_full_record`'s check."""
        if user.role is Role.LAB_TECHNICIAN:
            return True
        return await self.can_view_full_record(user, patient_id)

    def can_view_ssn(self, user: CurrentUser, patient_id: UUID) -> bool:
        """Field-level rule: SSN is withheld even from a treating doctor
        or nurse by default. Only the platform admin or the patient
        themselves can read it — object-level access to a patient's
        record does not imply access to every field on it."""
        if user.role is Role.ADMIN:
            return True
        return user.role is Role.PATIENT and user.patient_id == patient_id

    async def filter_accessible_patient_ids(
        self, user: CurrentUser, patient_ids: set[UUID]
    ) -> set[UUID]:
        """Batched version of `can_view_full_record`, used to scope list
        queries (`patients`) in one query instead of one check per id."""
        if user.role is Role.ADMIN:
            return set(patient_ids)
        if user.role is Role.PATIENT:
            return patient_ids & ({user.patient_id} if user.patient_id else set())
        if user.role in _CLINICAL_ROLES and user.provider_id is not None:
            return await self._relationships.bulk_has_active_relationship(
                provider_id=user.provider_id, patient_ids=list(patient_ids)
            )
        return set()

    async def require_full_record_access(self, user: CurrentUser, patient_id: UUID) -> None:
        if not await self.can_view_full_record(user, patient_id):
            raise AuthorizationError(
                "You do not have an active clinical relationship with this patient."
            )

    async def require_lab_result_access(self, user: CurrentUser, patient_id: UUID) -> None:
        if not await self.can_view_lab_results(user, patient_id):
            raise AuthorizationError(
                "You do not have access to this patient's lab results."
            )
