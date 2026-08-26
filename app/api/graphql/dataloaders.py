"""Per-request DataLoaders — the mechanism that keeps this schema from
degrading into N+1 queries.

Strawberry resolves sibling fields concurrently, so ten `patients { ...
} { primaryProvider { name } }` selections each call `.load(provider_id)`
in the same event-loop tick. A DataLoader coalesces every `.load()` call
made before the batch function actually runs into one `batch_load_fn`
invocation — ten individual provider lookups become one
`WHERE id IN (...)` query. This module builds one full set of loaders
per GraphQL request (never shared across requests, so nothing cached
here can leak between callers or outlive one request's own writes).
"""

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from app.repositories.base import BaseRepository, PatientScopedRepository
from app.repositories.clinical import (
    AllergyRepository,
    DiagnosisRepository,
    EncounterRepository,
    MedicationRepository,
    ProcedureRepository,
)
from app.repositories.observations import LabResultRepository, VitalSignRepository
from app.repositories.patient import PatientRepository
from app.repositories.provider import FacilityRepository, ProviderRepository


def _by_id_loader(repo: BaseRepository) -> Callable[[Sequence[UUID]], Awaitable[list]]:
    async def batch_load(ids: Sequence[UUID]) -> list:
        found = {item.id: item for item in await repo.get_by_ids(ids)}
        return [found.get(id_) for id_ in ids]

    return batch_load


def _by_patient_loader(
    repo: PatientScopedRepository,
) -> Callable[[Sequence[UUID]], Awaitable[list]]:
    async def batch_load(patient_ids: Sequence[UUID]) -> list:
        grouped = await repo.list_by_patient_ids(patient_ids)
        return [grouped.get(pid, []) for pid in patient_ids]

    return batch_load


@dataclass(slots=True)
class DataLoaders:
    patients_by_id: DataLoader
    providers_by_id: DataLoader
    facilities_by_id: DataLoader
    encounters_by_patient: DataLoader
    diagnoses_by_patient: DataLoader
    medications_by_patient: DataLoader
    allergies_by_patient: DataLoader
    procedures_by_patient: DataLoader
    lab_results_by_patient: DataLoader
    vital_signs_by_patient: DataLoader


def build_dataloaders(session: AsyncSession) -> DataLoaders:
    return DataLoaders(
        patients_by_id=DataLoader(load_fn=_by_id_loader(PatientRepository(session))),
        providers_by_id=DataLoader(load_fn=_by_id_loader(ProviderRepository(session))),
        facilities_by_id=DataLoader(load_fn=_by_id_loader(FacilityRepository(session))),
        encounters_by_patient=DataLoader(
            load_fn=_by_patient_loader(EncounterRepository(session))
        ),
        diagnoses_by_patient=DataLoader(
            load_fn=_by_patient_loader(DiagnosisRepository(session))
        ),
        medications_by_patient=DataLoader(
            load_fn=_by_patient_loader(MedicationRepository(session))
        ),
        allergies_by_patient=DataLoader(
            load_fn=_by_patient_loader(AllergyRepository(session))
        ),
        procedures_by_patient=DataLoader(
            load_fn=_by_patient_loader(ProcedureRepository(session))
        ),
        lab_results_by_patient=DataLoader(
            load_fn=_by_patient_loader(LabResultRepository(session))
        ),
        vital_signs_by_patient=DataLoader(
            load_fn=_by_patient_loader(VitalSignRepository(session))
        ),
    )
