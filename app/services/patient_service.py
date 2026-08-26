"""Cache-aside reads for the `Patient` aggregate.

`patient(id)` is the single most repeated lookup in this API — every
encounter, medication, lab result, and timeline entry resolves back to
its parent patient — while a patient's demographic record changes far
less often than it's read. That access pattern is exactly what
cache-aside is for: check Redis first, fall back to Postgres on a miss,
and populate the cache for next time.

This lives in the service layer rather than the repository so the
repository stays a pure data-access layer and the invalidation policy —
what has to be cleared when a patient record changes — stays in one
place, next to the read path it affects.
"""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.cache_service import CacheService
from app.models.enums import Sex
from app.models.patient import Patient
from app.repositories.patient import PatientRepository

_PATIENT_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True, slots=True)
class PatientRecord:
    """Cache-friendly projection of a `Patient` row. GraphQL resolvers
    work against this instead of the ORM model directly so a cache hit
    and a cache miss hand back an identical shape either way."""

    id: UUID
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    sex: Sex
    phone: str | None
    email: str | None
    address: str | None
    ssn: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, patient: Patient) -> "PatientRecord":
        return cls(
            id=patient.id,
            mrn=patient.mrn,
            first_name=patient.first_name,
            last_name=patient.last_name,
            date_of_birth=patient.date_of_birth,
            sex=patient.sex,
            phone=patient.phone,
            email=patient.email,
            address=patient.address,
            ssn=patient.ssn,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )

    def to_cache(self) -> str:
        payload = asdict(self)
        payload["id"] = str(self.id)
        payload["sex"] = self.sex.value
        payload["date_of_birth"] = self.date_of_birth.isoformat()
        payload["created_at"] = self.created_at.isoformat()
        payload["updated_at"] = self.updated_at.isoformat()
        return json.dumps(payload)

    @classmethod
    def from_cache(cls, raw: str) -> "PatientRecord":
        payload = json.loads(raw)
        return cls(
            id=UUID(payload["id"]),
            mrn=payload["mrn"],
            first_name=payload["first_name"],
            last_name=payload["last_name"],
            date_of_birth=date.fromisoformat(payload["date_of_birth"]),
            sex=Sex(payload["sex"]),
            phone=payload["phone"],
            email=payload["email"],
            address=payload["address"],
            ssn=payload["ssn"],
            created_at=datetime.fromisoformat(payload["created_at"]),
            updated_at=datetime.fromisoformat(payload["updated_at"]),
        )


def _cache_key(patient_id: UUID) -> str:
    return f"patient:{patient_id}"


class PatientService:
    def __init__(self, session: AsyncSession, cache: CacheService) -> None:
        self.repo = PatientRepository(session)
        self.cache = cache

    async def get_patient(self, patient_id: UUID) -> PatientRecord | None:
        key = _cache_key(patient_id)

        cached = await self.cache.get(key)
        if cached is not None:
            return PatientRecord.from_cache(cached)

        patient = await self.repo.get_by_id(patient_id)
        if patient is None:
            return None

        record = PatientRecord.from_model(patient)
        await self.cache.set(key, record.to_cache(), ttl_seconds=_PATIENT_CACHE_TTL_SECONDS)
        return record

    async def invalidate(self, patient_id: UUID) -> None:
        """Called by any mutation that writes to the `patients` table
        directly. Encounters, diagnoses, etc. don't need this — they
        don't change anything cached under the patient key itself."""
        await self.cache.delete(_cache_key(patient_id))
