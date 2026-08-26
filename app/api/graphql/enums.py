"""GraphQL enum wrappers around the domain enums in `app.models.enums`.

Wrapping (rather than redefining) keeps the GraphQL schema and the
database's native Postgres enums from drifting apart — there is exactly
one definition of what a `Role` or `EncounterStatus` is.
"""

import strawberry

from app.models import enums as domain

Role = strawberry.enum(domain.Role, name="Role")
Sex = strawberry.enum(domain.Sex, name="Sex")
FacilityType = strawberry.enum(domain.FacilityType, name="FacilityType")
RelationshipType = strawberry.enum(domain.RelationshipType, name="RelationshipType")
EncounterType = strawberry.enum(domain.EncounterType, name="EncounterType")
EncounterStatus = strawberry.enum(domain.EncounterStatus, name="EncounterStatus")
DiagnosisStatus = strawberry.enum(domain.DiagnosisStatus, name="DiagnosisStatus")
MedicationStatus = strawberry.enum(domain.MedicationStatus, name="MedicationStatus")
AllergySeverity = strawberry.enum(domain.AllergySeverity, name="AllergySeverity")
VitalSignType = strawberry.enum(domain.VitalSignType, name="VitalSignType")
AbnormalFlag = strawberry.enum(domain.AbnormalFlag, name="AbnormalFlag")
