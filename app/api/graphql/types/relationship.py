from datetime import date

import strawberry

from app.api.graphql.enums import RelationshipType
from app.models.relationship import PatientProviderRelationship as RelationshipModel


@strawberry.type(
    description=(
        "A clinical relationship between a patient and a provider — the "
        "record that grants a DOCTOR/NURSE access to a patient's data."
    )
)
class PatientProviderRelationship:
    id: strawberry.ID
    relationship_type: RelationshipType
    start_date: date
    end_date: date | None
    active: bool

    @classmethod
    def from_model(cls, relationship: RelationshipModel) -> "PatientProviderRelationship":
        return cls(
            id=strawberry.ID(str(relationship.id)),
            relationship_type=relationship.relationship_type,
            start_date=relationship.start_date,
            end_date=relationship.end_date,
            active=relationship.active,
        )
