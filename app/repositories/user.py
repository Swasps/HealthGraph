from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update

from app.models.enums import Role
from app.models.user import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def create(self, *, email: str, hashed_password: str, role: Role) -> User:
        user = User(email=email, hashed_password=hashed_password, role=role)
        return self.add(user)


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def create(self, *, user_id: UUID, token_hash: str, expires_at: datetime) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        return self.add(token)

    async def revoke(self, token: RefreshToken) -> None:
        token.revoked = True

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        """Used on password change / suspected compromise: invalidate
        every outstanding session for the account in one statement rather
        than loading and revoking rows one at a time."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.session.execute(stmt)
