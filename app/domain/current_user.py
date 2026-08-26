from dataclasses import dataclass
from uuid import UUID

from app.models.enums import Role


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """The resolved identity behind a request: decoded once from the JWT
    plus a lookup of the linked Patient/Provider row, then threaded
    through REST dependencies and the GraphQL context so every resolver
    and policy check works against the same object instead of re-deriving
    it from scratch."""

    user_id: UUID
    role: Role
    patient_id: UUID | None = None
    provider_id: UUID | None = None

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN
