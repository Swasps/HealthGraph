"""Relay-style cursor connections, generic over the node type.

One generic `Connection[T]` means every paginated field in the schema —
`patients`, `patientEncounters`, `patientMedications`, `patientLabResults`
— exposes the same `edges { cursor node }` / `pageInfo` shape instead of
each hand-rolling its own paginated wrapper type.
"""

from collections.abc import Callable
from typing import Generic, TypeVar

import strawberry

from app.repositories.pagination import Page

NodeType = TypeVar("NodeType")


@strawberry.type(description="Cursor-pagination metadata, per the Relay Cursor Connections spec.")
class PageInfo:
    has_next_page: bool
    has_previous_page: bool
    start_cursor: str | None
    end_cursor: str | None


@strawberry.type
class Edge(Generic[NodeType]):
    cursor: str
    node: NodeType


@strawberry.type
class Connection(Generic[NodeType]):
    edges: list[Edge[NodeType]]
    page_info: PageInfo


def to_connection(page: Page, to_node: Callable[..., NodeType]) -> Connection[NodeType]:
    return Connection(
        edges=[Edge(cursor=page.cursor_for(item), node=to_node(item)) for item in page.items],
        page_info=PageInfo(
            has_next_page=page.has_next_page,
            has_previous_page=page.has_previous_page,
            start_cursor=page.start_cursor,
            end_cursor=page.end_cursor,
        ),
    )
