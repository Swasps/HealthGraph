"""All ORM models are imported here so a single `import app.models` (as
done by Alembic's env.py) registers the full schema on Base.metadata."""

from app.models.facility import Facility
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.relationship import PatientProviderRelationship
from app.models.user import RefreshToken, User

__all__ = [
    "Facility",
    "Patient",
    "PatientProviderRelationship",
    "Provider",
    "RefreshToken",
    "User",
]
