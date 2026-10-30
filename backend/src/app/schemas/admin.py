from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import UserRole


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class AdminUserDetail(AdminUserSummary):
    email: EmailStr


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminRoleUpdate(BaseModel):
    role: UserRole
