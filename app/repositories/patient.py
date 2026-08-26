from datetime import date, datetime

from sqlalchemy import Select, or_, select

from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.repositories.pagination import KeysetSpec, Page, paginate


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    async def get_by_mrn(self, mrn: str) -> Patient | None:
        stmt = select(Patient).where(Patient.mrn == mrn)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        name: str | None,
        first: int,
        after: str | None,
    ) -> Page[Patient]:
        """Cursor-paginated patient search. `name` matches against either
        name field; callers needing patient-scoped access control (a
        doctor's own panel, say) should further restrict `stmt` before
        this is called — this repository has no opinion on who's allowed
        to see what.
        """
        stmt: Select = select(Patient)
        if name:
            pattern = f"%{name}%"
            stmt = stmt.where(
                or_(Patient.first_name.ilike(pattern), Patient.last_name.ilike(pattern))
            )

        spec = KeysetSpec(
            sort_column=Patient.created_at,
            id_column=Patient.id,
            parse_sort_value=datetime.fromisoformat,
            descending=True,
        )
        return await paginate(self.session, stmt, spec, first, after)

    async def search_within(
        self,
        patient_ids: set,
        *,
        name: str | None,
        first: int,
        after: str | None,
    ) -> Page[Patient]:
        """Same as `search`, but constrained to a caller-supplied set of
        patient ids — this is what a DOCTOR/NURSE-scoped `patients` query
        uses once the access policy has resolved which patients they may
        see.
        """
        stmt: Select = select(Patient).where(Patient.id.in_(patient_ids))
        if name:
            pattern = f"%{name}%"
            stmt = stmt.where(
                or_(Patient.first_name.ilike(pattern), Patient.last_name.ilike(pattern))
            )

        spec = KeysetSpec(
            sort_column=Patient.created_at,
            id_column=Patient.id,
            parse_sort_value=datetime.fromisoformat,
            descending=True,
        )
        return await paginate(self.session, stmt, spec, first, after)

    async def create(
        self,
        *,
        mrn: str,
        first_name: str,
        last_name: str,
        date_of_birth: date,
        sex,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        ssn: str | None = None,
    ) -> Patient:
        patient = Patient(
            mrn=mrn,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            sex=sex,
            phone=phone,
            email=email,
            address=address,
            ssn=ssn,
        )
        return self.add(patient)
