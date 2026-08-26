"""Cursor (keyset) pagination.

OFFSET-based pagination degrades linearly with page depth — `OFFSET 50000`
still has to scan and discard 50,000 rows. Keyset pagination instead
carries the last-seen row's sort key in an opaque cursor and asks the
database for "everything after that point", which a composite index
answers in effectively constant time regardless of how deep the caller
has paged. This module implements that scheme once, generically, so every
paginated list resolver (patients, encounters, lab results, ...) shares
it instead of reimplementing offset math per entity.
"""

import base64
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ItemT = TypeVar("ItemT")

_CURSOR_SEPARATOR = "\x1f"


def encode_cursor(*parts: Any) -> str:
    raw = _CURSOR_SEPARATOR.join(str(p) for p in parts)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> list[str]:
    raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    return raw.split(_CURSOR_SEPARATOR)


@dataclass(frozen=True, slots=True)
class KeysetSpec:
    """Describes the (sort_column, id_column) pair a query is paginated
    on. `id_column` is always the tiebreaker so rows with an identical
    sort value (e.g. two encounters started in the same second) still get
    a stable, gap-free ordering."""

    sort_column: InstrumentedAttribute
    id_column: InstrumentedAttribute
    parse_sort_value: Callable[[str], Any]
    descending: bool = True


@dataclass(slots=True)
class Page(Generic[ItemT]):
    items: list[ItemT]
    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None
    cursor_for: Callable[[ItemT], str]

    @classmethod
    def empty(cls) -> "Page[ItemT]":
        return cls(
            items=[],
            has_next_page=False,
            has_previous_page=False,
            start_cursor=None,
            end_cursor=None,
            cursor_for=lambda _item: "",
        )


async def paginate(
    session: AsyncSession,
    stmt: Select,
    spec: KeysetSpec,
    first: int,
    after: str | None,
) -> Page:
    """`first`/`after` mirror the Relay Cursor Connections spec. We over-
    fetch by one row to know whether a next page exists without a second
    COUNT query.

    Note on `has_previous_page`: a fully spec-compliant answer would
    require a second keyset lookup in the opposite direction. We instead
    infer it from whether a cursor was supplied at all, which is correct
    for the sequential-paging access pattern every caller in this API
    actually uses (there is no "jump to last page" UI) and avoids doubling
    the query count on every page fetch.
    """
    order_sort = spec.sort_column.desc() if spec.descending else spec.sort_column.asc()
    order_id = spec.id_column.desc() if spec.descending else spec.id_column.asc()
    stmt = stmt.order_by(order_sort, order_id)

    if after is not None:
        sort_raw, id_raw = decode_cursor(after)
        sort_value = spec.parse_sort_value(sort_raw)
        id_value = UUID(id_raw)
        boundary = (
            spec.sort_column < sort_value
            if spec.descending
            else spec.sort_column > sort_value
        )
        tie = and_(spec.sort_column == sort_value, spec.id_column < id_value) \
            if spec.descending \
            else and_(spec.sort_column == sort_value, spec.id_column > id_value)
        stmt = stmt.where(or_(boundary, tie))

    result = await session.execute(stmt.limit(first + 1))
    rows = list(result.scalars().all())

    has_next_page = len(rows) > first
    items = rows[:first]

    def cursor_for(item: Any) -> str:
        return encode_cursor(getattr(item, spec.sort_column.key), item.id)

    return Page(
        items=items,
        has_next_page=has_next_page,
        has_previous_page=after is not None,
        start_cursor=cursor_for(items[0]) if items else None,
        end_cursor=cursor_for(items[-1]) if items else None,
        cursor_for=cursor_for,
    )
