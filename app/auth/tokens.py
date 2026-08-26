"""JWT access tokens and opaque refresh tokens.

Access tokens are short-lived, stateless, and never touch the database on
verification — that's the point of a JWT. Refresh tokens are the opposite
on purpose: long-lived and stateful, so a compromised one can be revoked
server-side. We never store a refresh token's raw value, only a SHA-256
hash of it (see `app.repositories.user.RefreshTokenRepository`), so a
database leak alone doesn't hand out valid sessions.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError
from app.models.enums import Role

settings = get_settings()


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    role: Role
    expires_at: datetime


def create_access_token(*, user_id: UUID, role: Role) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "access",
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("access token has expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("invalid access token") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("token is not an access token")

    try:
        return AccessTokenClaims(
            user_id=UUID(payload["sub"]),
            role=Role(payload["role"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("malformed access token") from exc


def generate_refresh_token() -> str:
    """The raw, URL-safe token handed to the client. High entropy stands
    in for a signature here — unlike the access token there's nothing to
    verify offline, so it just needs to be unguessable."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
