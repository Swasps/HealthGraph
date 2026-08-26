from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import FacilityType, Role


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FacilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    facility_type: FacilityType
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=20)


class FacilityOut(BaseModel):
    id: UUID
    name: str
    facility_type: FacilityType
    address: str | None
    phone: str | None

    model_config = {"from_attributes": True}


class AuditLogOut(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogOut]
    has_next_page: bool
    end_cursor: str | None
