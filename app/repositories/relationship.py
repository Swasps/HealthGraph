from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.models.relationship import PatientProviderRelationship
from app.repositories.base import BaseRepository


class PatientProviderRelationshipRepository(BaseRepository[PatientProviderRelationship]):
    """Backs the access-policy layer. Every check here is deliberately a
    single indexed query (see `ix_ppr_provider_active` /
    `ix_ppr_patient_active`) since it runs on the hot path of nearly every
    patient-scoped GraphQL field."""

    model = PatientProviderRelationship

    async def has_active_relationship(self, *, patient_id: UUID, provider_id: UUID) -> bool:
        stmt = select(PatientProviderRelationship.id).where(
            PatientProviderRelationship.patient_id == patient_id,
            PatientProviderRelationship.provider_id == provider_id,
            PatientProviderRelationship.active.is_(True),
        )
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def accessible_patient_ids(self, *, provider_id: UUID) -> set[UUID]:
        """The full set of patients a provider currently has a clinical
        relationship with — used to scope the `patients` list query so a
        doctor's search only ever ranges over their own panel."""
        stmt = select(PatientProviderRelationship.patient_id).where(
            PatientProviderRelationship.provider_id == provider_id,
            PatientProviderRelationship.active.is_(True),
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    def create(
        self,
        *,
        patient_id: UUID,
        provider_id: UUID,
        relationship_type,
        start_date: date,
    ) -> PatientProviderRelationship:
        relationship = PatientProviderRelationship(
            patient_id=patient_id,
            provider_id=provider_id,
            relationship_type=relationship_type,
            start_date=start_date,
        )
        return self.add(relationship)

    async def bulk_has_active_relationship(
        self, *, provider_id: UUID, patient_ids: Sequence[UUID]
    ) -> set[UUID]:
        """Batched variant of `has_active_relationship` for a DataLoader:
        one query to authorize N patients instead of N."""
        if not patient_ids:
            return set()
        stmt = select(PatientProviderRelationship.patient_id).where(
            PatientProviderRelationship.provider_id == provider_id,
            PatientProviderRelationship.patient_id.in_(patient_ids),
            PatientProviderRelationship.active.is_(True),
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())
