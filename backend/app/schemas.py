from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ModerationAction, ReportStatus, UserRole, VideoStatus


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    caption: str | None
    size_bytes: int
    status: VideoStatus
    created_at: datetime


class LabelResponse(BaseModel):
    name: str
    confidence: float
    level: str


class AIResultResponse(BaseModel):
    video_id: UUID
    job_status: str
    transcript: str | None
    labels: list[LabelResponse]


class ReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    reason: str
    status: ReportStatus


class ModerationDecisionRequest(BaseModel):
    action: ModerationAction
    reason: str | None = Field(default=None, max_length=1000)
