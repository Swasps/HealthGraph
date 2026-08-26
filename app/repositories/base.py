from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.database.base import Base
from app.repositories.pagination import KeysetSpec, Page, paginate

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin data-access layer: one repository per aggregate, all SQL for
    that aggregate lives here rather than scattered across services and
    resolvers. Keeping this dumb (no business rules) makes it easy to unit
    test services against a fake repository if ever needed."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id_: UUID) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def get_by_ids(self, ids: Sequence[UUID]) -> list[ModelT]:
        """Batch fetch by primary key. This is what backs every DataLoader:
        one query for N ids instead of N queries, regardless of how many
        GraphQL fields ask for this entity in the same request."""
        if not ids:
            return []
        stmt = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)


class PatientScopedRepository(BaseRepository[ModelT]):
    """Shared behavior for every clinical entity that hangs off a patient
    (encounters, diagnoses, medications, ...). Concrete repositories only
    need to declare `patient_id_column` and `sort_column`; the batched
    lookup and cursor pagination are implemented once here.
    """

    patient_id_column: InstrumentedAttribute
    sort_column: InstrumentedAttribute
    sort_parser: Callable[[str], Any] = staticmethod(datetime.fromisoformat)

    async def list_by_patient_ids(
        self, patient_ids: Sequence[UUID]
    ) -> dict[UUID, list[ModelT]]:
        """One query, grouped in Python by patient id — the batch load
        function every per-patient DataLoader in the GraphQL layer calls.
        """
        if not patient_ids:
            return {}
        stmt = (
            select(self.model)
            .where(self.patient_id_column.in_(patient_ids))
            .order_by(self.sort_column.desc())
        )
        result = await self.session.execute(stmt)
        grouped: dict[UUID, list[ModelT]] = defaultdict(list)
        for row in result.scalars():
            grouped[getattr(row, self.patient_id_column.key)].append(row)
        return grouped

    async def paginate_by_patient(
        self, patient_id: UUID, first: int, after: str | None
    ) -> Page[ModelT]:
        stmt = select(self.model).where(self.patient_id_column == patient_id)
        spec = KeysetSpec(
            sort_column=self.sort_column,
            id_column=self.model.id,
            parse_sort_value=self.sort_parser,
            descending=True,
        )
        return await paginate(self.session, stmt, spec, first, after)
