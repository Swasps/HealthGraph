"""Shared input validation for mutation resolvers.

Kept as plain functions independent of GraphQL so the same rules could
back a future REST write endpoint without duplicating them. Each raises
`ValidationError` (mapped to a structured 422/GraphQL error) rather than
letting a blank string or an impossible date range reach the database.
"""

from datetime import UTC, date, datetime

from app.core.errors import ValidationError


def require_non_empty(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{field} must not be empty.")
    return stripped


def require_not_future(value: date, field: str) -> date:
    if value > datetime.now(UTC).date():
        raise ValidationError(f"{field} cannot be in the future.")
    return value


def require_date_order(
    start: date, end: date | None, *, start_field: str, end_field: str
) -> None:
    if end is not None and end < start:
        raise ValidationError(f"{end_field} cannot be before {start_field}.")


def require_positive(value: float, field: str) -> float:
    if value <= 0:
        raise ValidationError(f"{field} must be a positive number.")
    return value
