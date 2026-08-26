from datetime import datetime
from typing import Annotated

import strawberry

from app.api.graphql.types.clinical import Diagnosis, Encounter, Medication, Procedure
from app.api.graphql.types.observations import LabResult, VitalSign
from app.services.timeline_service import TimelineEventKind, TimelineItem

TimelineEvent = Annotated[
    Encounter | Diagnosis | Medication | LabResult | Procedure | VitalSign,
    strawberry.union("TimelineEvent"),
]

_BUILDERS = {
    TimelineEventKind.ENCOUNTER: Encounter.from_model,
    TimelineEventKind.DIAGNOSIS: Diagnosis.from_model,
    TimelineEventKind.MEDICATION: Medication.from_model,
    TimelineEventKind.LAB_RESULT: LabResult.from_model,
    TimelineEventKind.PROCEDURE: Procedure.from_model,
    TimelineEventKind.VITAL_SIGN: VitalSign.from_model,
}


@strawberry.type(
    description=(
        "One entry in a patient's chronological timeline. `occurredAt` is "
        "normalized across all six underlying event types so clients can "
        "sort/display without inspecting which concrete type `event` is."
    )
)
class TimelineEntry:
    occurred_at: datetime
    event: TimelineEvent

    @classmethod
    def from_item(cls, item: TimelineItem) -> "TimelineEntry":
        return cls(occurred_at=item.occurred_at, event=_BUILDERS[item.kind](item.model))
