from sqlalchemy import select

from app.models.facility import Facility
from app.models.provider import Provider
from app.repositories.base import BaseRepository


class ProviderRepository(BaseRepository[Provider]):
    model = Provider

    async def get_by_npi(self, npi_number: str) -> Provider | None:
        stmt = select(Provider).where(Provider.npi_number == npi_number)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id) -> Provider | None:
        stmt = select(Provider).where(Provider.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_facility(self, facility_id) -> list[Provider]:
        stmt = select(Provider).where(Provider.facility_id == facility_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class FacilityRepository(BaseRepository[Facility]):
    model = Facility

    async def list_all(self) -> list[Facility]:
        result = await self.session.execute(select(Facility).order_by(Facility.name))
        return list(result.scalars().all())
