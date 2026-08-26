from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.models.records import AuditLog
from app.repositories.base import BaseRepository
from app.repositories.pagination import KeysetSpec, Page, paginate


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def create(
        self,
        *,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None,
        ip_address: str | None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details,
        )
        return self.add(entry)

    async def list_page(self, *, first: int, after: str | None) -> Page[AuditLog]:
        stmt = select(AuditLog)
        spec = KeysetSpec(
            sort_column=AuditLog.occurred_at,
            id_column=AuditLog.id,
            parse_sort_value=datetime.fromisoformat,
            descending=True,
        )
        return await paginate(self.session, stmt, spec, first, after)
