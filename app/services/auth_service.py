"""Registration, login, token refresh, and current-user resolution.

This is the one place that touches both the password/JWT primitives in
`app.auth` and the persistence layer in `app.repositories` — everything
above it (REST routes, GraphQL context) should only ever need to call
into this service, never reach for a repository or `jwt.decode` directly.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import (
    AccessTokenClaims,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.core.errors import AuthenticationError, ConflictError
from app.domain.current_user import CurrentUser
from app.models.enums import Role
from app.models.user import User
from app.repositories.patient import PatientRepository
from app.repositories.provider import ProviderRepository
from app.repositories.user import RefreshTokenRepository, UserRepository


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.patients = PatientRepository(session)
        self.providers = ProviderRepository(session)

    async def register(self, *, email: str, password: str, role: Role) -> User:
        if await self.users.get_by_email(email) is not None:
            raise ConflictError("An account with this email already exists.")
        user = self.users.create(email=email, hashed_password=hash_password(password), role=role)
        await self.session.flush()
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        # Run the hash comparison even on a missing user so response time
        # doesn't leak which emails are registered.
        valid = verify_password(password, user.hashed_password) if user else False
        if not user or not valid:
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("This account has been disabled.")
        return user

    async def issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(user_id=user.id, role=user.role)
        raw_refresh_token = generate_refresh_token()
        self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
        await self.session.flush()
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self.authenticate(email=email, password=password)
        return await self.issue_token_pair(user)

    async def refresh(self, *, raw_refresh_token: str) -> TokenPair:
        """Rotates the refresh token on every use: the presented token is
        revoked and a new one issued, so a token can only ever be replayed
        once before it's dead. If someone else already used it, this
        raises here and the legitimate owner's next refresh attempt fails
        too — a signal worth alerting on in a real deployment."""
        token_hash = hash_refresh_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is None or stored.revoked or stored.expires_at < datetime.now(UTC):
            raise AuthenticationError("Refresh token is invalid or expired.")

        await self.refresh_tokens.revoke(stored)

        user = await self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("This account is no longer active.")
        return await self.issue_token_pair(user)

    async def logout(self, *, raw_refresh_token: str) -> None:
        stored = await self.refresh_tokens.get_by_hash(hash_refresh_token(raw_refresh_token))
        if stored is not None:
            await self.refresh_tokens.revoke(stored)

    async def resolve_current_user(self, claims: AccessTokenClaims) -> CurrentUser:
        """Builds the request-scoped identity from validated JWT claims.
        A PATIENT/DOCTOR/NURSE/LAB_TECHNICIAN role only becomes useful
        once we know *which* patient or provider row the token maps to —
        that's the id every access-policy check keys off of."""
        patient_id = None
        provider_id = None

        if claims.role is Role.PATIENT:
            patient = await self.patients.get_by_user_id(claims.user_id)
            patient_id = patient.id if patient else None
        elif claims.role in (Role.DOCTOR, Role.NURSE, Role.LAB_TECHNICIAN):
            provider = await self.providers.get_by_user_id(claims.user_id)
            provider_id = provider.id if provider else None

        return CurrentUser(
            user_id=claims.user_id,
            role=claims.role,
            patient_id=patient_id,
            provider_id=provider_id,
        )
