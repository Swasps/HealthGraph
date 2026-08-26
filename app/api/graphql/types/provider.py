import strawberry

from app.api.graphql.context import GraphQLContext
from app.api.graphql.enums import FacilityType as FacilityCategory
from app.models.facility import Facility as FacilityModel
from app.models.provider import Provider as ProviderModel


@strawberry.type(description="A hospital, clinic, lab, or pharmacy.")
class Facility:
    id: strawberry.ID
    name: str
    facility_type: FacilityCategory
    address: str | None
    phone: str | None

    @classmethod
    def from_model(cls, facility: FacilityModel) -> "Facility":
        return cls(
            id=strawberry.ID(str(facility.id)),
            name=facility.name,
            facility_type=facility.facility_type,
            address=facility.address,
            phone=facility.phone,
        )


@strawberry.type(description="A clinician: doctor, nurse, or lab technician.")
class Provider:
    id: strawberry.ID
    first_name: str
    last_name: str
    npi_number: str
    specialty: str | None

    _facility_id: strawberry.Private[str]

    @strawberry.field(description="The facility this provider practices at.")
    async def facility(self, info: strawberry.Info[GraphQLContext, None]) -> Facility:
        facility_model = await info.context.loaders.facilities_by_id.load(
            self._facility_id
        )
        return Facility.from_model(facility_model)

    @classmethod
    def from_model(cls, provider: ProviderModel) -> "Provider":
        return cls(
            id=strawberry.ID(str(provider.id)),
            first_name=provider.first_name,
            last_name=provider.last_name,
            npi_number=provider.npi_number,
            specialty=provider.specialty,
            _facility_id=provider.facility_id,
        )
