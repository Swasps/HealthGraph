"""All ORM models are imported here so a single `import app.models` (as
done by Alembic's env.py) registers the full schema on Base.metadata."""

from app.models.clinical import Allergy, Diagnosis, Encounter, Medication, Procedure
from app.models.facility import Facility
from app.models.observations import LabResult, VitalSign
from app.models.patient import Patient
from app.models.provider import Provider
from app.models.records import AuditLog, MedicalRecord
from app.models.relationship import PatientProviderRelationship
from app.models.user import RefreshToken, User

__all__ = [
    "Allergy",
    "AuditLog",
    "Diagnosis",
    "Encounter",
    "Facility",
    "LabResult",
    "MedicalRecord",
    "Medication",
    "Patient",
    "PatientProviderRelationship",
    "Procedure",
    "Provider",
    "RefreshToken",
    "User",
    "VitalSign",
]
