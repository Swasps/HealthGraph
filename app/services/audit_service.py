"""Records who did what to which resource.

Called explicitly from services and GraphQL mutation resolvers at the
point of action, rather than inferred from HTTP verbs by a blanket
middleware. GraphQL multiplexes very different operations (a query and a
mutation are both just a POST to /graphql), so the only place that
reliably knows "a diagnosis was just added" is the code that added it.

Audit writes commit through their own session rather than the caller's
request-scoped one, on purpose: a failed login or a mutation that gets
rolled back after an authorization check still needs its audit entry to
survive, since those are exactly the events worth recording. Piggybacking
on the caller's transaction would silently lose them whenever that
transaction never reaches `commit()`.
"""

from uuid import UUID

from app.database.session import AsyncSessionLocal
from app.middleware.request_context import client_ip_var
from app.repositories.audit import AuditLogRepository


class AuditService:
    async def record(
        self,
        *,
        user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        ip_address = client_ip_var.get()
        async with AsyncSessionLocal() as session:
            AuditLogRepository(session).create(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                details=details,
            )
            await session.commit()
