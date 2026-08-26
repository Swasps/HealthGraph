import enum


class Role(str, enum.Enum):
    """Application-level roles used for RBAC. Deliberately small and
    closed — new roles are a schema migration, not a config toggle,
    because each one is wired into the authorization policy explicitly."""

    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    PATIENT = "PATIENT"


class Sex(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class RelationshipType(str, enum.Enum):
    PRIMARY_CARE = "PRIMARY_CARE"
    ATTENDING = "ATTENDING"
    CONSULTING = "CONSULTING"
    REFERRING = "REFERRING"


class EncounterType(str, enum.Enum):
    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"
    EMERGENCY = "EMERGENCY"
    TELEHEALTH = "TELEHEALTH"


class EncounterStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DiagnosisStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    CHRONIC = "CHRONIC"


class MedicationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DISCONTINUED = "DISCONTINUED"


class AllergySeverity(str, enum.Enum):
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"


class VitalSignType(str, enum.Enum):
    BLOOD_PRESSURE = "BLOOD_PRESSURE"
    HEART_RATE = "HEART_RATE"
    TEMPERATURE = "TEMPERATURE"
    RESPIRATORY_RATE = "RESPIRATORY_RATE"
    OXYGEN_SATURATION = "OXYGEN_SATURATION"
    WEIGHT = "WEIGHT"
    HEIGHT = "HEIGHT"
    BMI = "BMI"


class AbnormalFlag(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FacilityType(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    LAB = "LAB"
    PHARMACY = "PHARMACY"
