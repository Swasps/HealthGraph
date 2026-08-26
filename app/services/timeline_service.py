"""Merges six clinical entity types into one chronological feed.

This is the query most likely to be misimplemented as N+1: naively,
you'd load a patient, then separately query their encounters, diagnoses,
medications, lab results, procedures, and vital signs — six round trips
per patient, or 6*N across a list of N patients. Every load here goes
through the request's DataLoaders instead, so resolving the timeline for
20 patients in one GraphQL query costs 6 queries total (one `IN (...)`
per entity type, covering all 20 patient ids), not 120 — see
`app.api.graphql.dataloaders` for the batching itself.

Pagination note: this returns a flat, `limit`-capped list rather than a
Relay connection. A cursor over a merge of six independently-sorted
sources would need a compound cursor (source table + per-table offset)
for marginal benefit here — callers who need deep paging over one entity
type already have the dedicated `patientEncounters` / `patientMedications`
/ `patientLabResults` queries for that.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import Enum
from typing import Any
from uuid import UUID

from app.api.graphql.dataloaders import DataLoaders

_MAX_TIMELINE_ENTRIES = 200


class TimelineEventKind(str, Enum):
    ENCOUNTER = "ENCOUNTER"
    DIAGNOSIS = "DIAGNOSIS"
    MEDICATION = "MEDICATION"
    LAB_RESULT = "LAB_RESULT"
    PROCEDURE = "PROCEDURE"
    VITAL_SIGN = "VITAL_SIGN"


@dataclass(frozen=True, slots=True)
class TimelineItem:
    occurred_at: datetime
    kind: TimelineEventKind
    model: Any


def _as_datetime(value: date | datetime) -> datetime:
    """Medication.start_date is a plain date; everything else on the
    timeline already carries a timezone-aware datetime. Normalizing here
    is what lets one `sort()` order all six sources together."""
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min, tzinfo=UTC)


async def build_patient_timeline(
    loaders: DataLoaders, patient_id: UUID, limit: int
) -> list[TimelineItem]:
    limit = min(max(limit, 1), _MAX_TIMELINE_ENTRIES)

    # Six independent loads, gathered rather than awaited one at a time:
    # this keeps one patient's own timeline latency down to the slowest
    # single query instead of the sum of all six, and — since nothing
    # here blocks before every `.load()` call is issued — still lets
    # DataLoader coalesce with the *same* loader being hit concurrently
    # for other patients elsewhere in this request.
    encounters, diagnoses, medications, lab_results, procedures, vital_signs = (
        await asyncio.gather(
            loaders.encounters_by_patient.load(patient_id),
            loaders.diagnoses_by_patient.load(patient_id),
            loaders.medications_by_patient.load(patient_id),
            loaders.lab_results_by_patient.load(patient_id),
            loaders.procedures_by_patient.load(patient_id),
            loaders.vital_signs_by_patient.load(patient_id),
        )
    )

    items: list[TimelineItem] = [
        *(
            TimelineItem(_as_datetime(e.started_at), TimelineEventKind.ENCOUNTER, e)
            for e in encounters
        ),
        *(
            TimelineItem(_as_datetime(d.diagnosed_at), TimelineEventKind.DIAGNOSIS, d)
            for d in diagnoses
        ),
        *(
            TimelineItem(_as_datetime(m.start_date), TimelineEventKind.MEDICATION, m)
            for m in medications
        ),
        *(
            TimelineItem(_as_datetime(lr.resulted_at), TimelineEventKind.LAB_RESULT, lr)
            for lr in lab_results
        ),
        *(
            TimelineItem(_as_datetime(p.performed_at), TimelineEventKind.PROCEDURE, p)
            for p in procedures
        ),
        *(
            TimelineItem(_as_datetime(v.recorded_at), TimelineEventKind.VITAL_SIGN, v)
            for v in vital_signs
        ),
    ]
    items.sort(key=lambda item: item.occurred_at, reverse=True)
    return items[:limit]
