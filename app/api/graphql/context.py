"""Per-request GraphQL context.

Built once per request via Strawberry's `context_getter` (itself a
FastAPI dependency, so `Depends(get_db_session)` gets the same
open-once/close-on-teardown lifecycle a REST route would get). Every
resolver reaches through `info.context` for its database session,
DataLoaders, and the caller's resolved identity — nothing here is looked
up twice per request.
"""

from dataclasses import dataclass, field

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import BaseContext

from app.api.graphql.dataloaders import DataLoaders, build_dataloaders
from app.auth.tokens import decode_access_token
from app.cache.cache_service import CacheService
from app.cache.client import redis_client
from app.core.errors import AuthenticationError
from app.database.session import get_db_session
from app.domain.access_policy import PatientAccessPolicy
from app.domain.current_user import CurrentUser
from app.repositories.relationship import PatientProviderRelationshipRepository
from app.services.auth_service import AuthService


@dataclass
class GraphQLContext(BaseContext):
    session: AsyncSession
    current_user: CurrentUser | None
    cache: CacheService = field(default_factory=lambda: CacheService(redis_client))
    loaders: DataLoaders = field(init=False)
    access_policy: PatientAccessPolicy = field(init=False)

    def __post_init__(self) -> None:
        self.loaders = build_dataloaders(self.session)
        self.access_policy = PatientAccessPolicy(
            PatientProviderRelationshipRepository(self.session)
        )

    def require_authenticated(self) -> CurrentUser:
        if self.current_user is None:
            raise AuthenticationError("Authentication required.")
        return self.current_user


async def get_graphql_context(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> GraphQLContext:
    current_user: CurrentUser | None = None
    authorization = request.headers.get("authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        try:
            claims = decode_access_token(token)
            current_user = await AuthService(session).resolve_current_user(claims)
        except AuthenticationError:
            # An invalid/expired token is treated as an anonymous caller;
            # resolvers that require auth reject via `require_authenticated`,
            # which gives a clearer error than failing context construction.
            current_user = None

    return GraphQLContext(session=session, current_user=current_user)
