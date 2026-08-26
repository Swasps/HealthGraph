from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.database.session import get_db_session
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)
) -> UserOut:
    service = AuthService(session)
    user = await service.register(email=payload.email, password=payload.password, role=payload.role)
    await session.commit()
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    service = AuthService(session)
    pair = await service.login(email=payload.email, password=payload.password)
    await session.commit()
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    service = AuthService(session)
    pair = await service.refresh(raw_refresh_token=payload.refresh_token)
    await session.commit()
    return TokenResponse(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshRequest, session: AsyncSession = Depends(get_db_session)
) -> None:
    service = AuthService(session)
    await service.logout(raw_refresh_token=payload.refresh_token)
    await session.commit()
