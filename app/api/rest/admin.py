"""System-administration REST surface.

Deliberately kept as REST rather than folded into the GraphQL schema:
these are operational endpoints (user directory, facility directory,
audit trail) consumed by internal tooling, not the patient-data API
surface GraphQL exists for. Every route here requires ADMIN.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.schemas import AuditLogOut, AuditLogPage, FacilityCreate, FacilityOut, UserOut
from app.auth.dependencies import require_roles
from app.database.session import get_db_session
from app.models.enums import Role
from app.models.facility import Facility
from app.repositories.audit import AuditLogRepository
from app.repositories.provider import FacilityRepository
from app.repositories.user import UserRepository

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.ADMIN))],
)


@router.get("/users", response_model=list[UserOut])
async def list_users(session: AsyncSession = Depends(get_db_session)) -> list[UserOut]:
    users = await UserRepository(session).list_all()
    return [UserOut.model_validate(u) for u in users]


@router.get("/facilities", response_model=list[FacilityOut])
async def list_facilities(session: AsyncSession = Depends(get_db_session)) -> list[FacilityOut]:
    facilities = await FacilityRepository(session).list_all()
    return [FacilityOut.model_validate(f) for f in facilities]


@router.post("/facilities", response_model=FacilityOut, status_code=status.HTTP_201_CREATED)
async def create_facility(
    payload: FacilityCreate, session: AsyncSession = Depends(get_db_session)
) -> FacilityOut:
    facility = Facility(
        name=payload.name,
        facility_type=payload.facility_type,
        address=payload.address,
        phone=payload.phone,
    )
    FacilityRepository(session).add(facility)
    await session.commit()
    return FacilityOut.model_validate(facility)


@router.get("/audit-logs", response_model=AuditLogPage)
async def list_audit_logs(
    first: int = Query(default=50, ge=1, le=200),
    after: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogPage:
    page = await AuditLogRepository(session).list_page(first=first, after=after)
    return AuditLogPage(
        items=[AuditLogOut.model_validate(entry) for entry in page.items],
        has_next_page=page.has_next_page,
        end_cursor=page.end_cursor,
    )
