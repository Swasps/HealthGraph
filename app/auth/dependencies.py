from collections.abc import Awaitable, Callable

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import decode_access_token
from app.core.errors import AuthenticationError, AuthorizationError
from app.database.session import get_db_session
from app.domain.current_user import CurrentUser
from app.models.enums import Role
from app.services.auth_service import AuthService


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    if authorization is None or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token.")

    token = authorization.removeprefix("Bearer ").strip()
    claims = decode_access_token(token)
    return await AuthService(session).resolve_current_user(claims)


def require_roles(*roles: Role) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Route-level RBAC guard. This only checks the role on the token —
    it says nothing about which specific patients a DOCTOR/NURSE may
    touch, which is the job of `app.domain.access_policy` further down
    the call stack."""

    async def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise AuthorizationError("You do not have permission to perform this action.")
        return user

    return _dependency
