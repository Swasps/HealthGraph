"""Structured application errors.

Every error the domain/service layer raises is one of these, so the API
layer (REST and GraphQL) can map them to a consistent shape instead of
leaking stack traces or ad-hoc dict payloads to clients.
"""

from __future__ import annotations


class HealthGraphError(Exception):
    """Base class for all handled application errors."""

    code = "internal_error"
    http_status = 500

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__


class NotFoundError(HealthGraphError):
    code = "not_found"
    http_status = 404


class ValidationError(HealthGraphError):
    code = "validation_error"
    http_status = 422


class AuthenticationError(HealthGraphError):
    code = "authentication_error"
    http_status = 401


class AuthorizationError(HealthGraphError):
    """Raised when a caller is authenticated but not permitted to act on
    the specific resource requested — e.g. a doctor with no relationship
    to the patient being queried."""

    code = "authorization_error"
    http_status = 403


class ConflictError(HealthGraphError):
    code = "conflict"
    http_status = 409


class RateLimitExceededError(HealthGraphError):
    code = "rate_limit_exceeded"
    http_status = 429


class QueryComplexityError(HealthGraphError):
    code = "query_too_complex"
    http_status = 400
