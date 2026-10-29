from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import AppealStatus, ModerationAction, ReportStatus, UserRole, VideoStatus


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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=10, max_length=512)


class PasswordForgotRequest(BaseModel):
    email: EmailStr


class PasswordForgotResponse(BaseModel):
    detail: str
    # Chỉ trả về khi environment khác "production" — xem mục bảo mật trong README.
    reset_token: str | None = None


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    current_password: str | None = Field(default=None, min_length=8, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ProfileUpdate":
        if self.display_name is None and self.new_password is None:
            raise ValueError("Phải cung cấp ít nhất một trường để cập nhật")
        if self.new_password is not None and self.current_password is None:
            raise ValueError("Cần current_password để đổi mật khẩu")
        return self


class LabelItem(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)


class LabelsUpdateRequest(BaseModel):
    labels: list[LabelItem] = Field(default_factory=list, max_length=50)


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


class VideoLabelInfo(BaseModel):
    name: str
    confidence: float
    level: str


class VideoSearchItem(BaseModel):
    id: UUID
    original_filename: str
    caption: str | None
    status: VideoStatus
    owner_display_name: str
    labels: list[VideoLabelInfo]
    created_at: datetime


class AppealCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class AppealResponse(BaseModel):
    id: UUID
    video_id: UUID
    user_id: UUID
    user_display_name: str
    reason: str
    status: AppealStatus
    moderator_id: UUID | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None


class AppealDecisionRequest(BaseModel):
    action: ModerationAction
    reason: str | None = Field(default=None, max_length=1000)


class AdminLabelResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    video_count: int


class AdminLabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class AdminLabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminLabelUpdate":
        if self.name is None and self.is_active is None:
            raise ValueError("Phải cung cấp ít nhất một trường để cập nhật")
        return self


class AdminVideoStatusUpdate(BaseModel):
    # "processing" không phải trạng thái chuyển bằng tay nên không có trong danh sách.
    status: Literal["pending_review", "published", "rejected", "deleted"]
    reason: str | None = Field(default=None, max_length=1000)


class ModeratorStatsResponse(BaseModel):
    moderator_id: UUID
    display_name: str
    role: UserRole
    videos_reviewed: int
    reviews_approved: int
    reviews_rejected: int
    appeals_handled: int


class LabelStat(BaseModel):
    name: str
    video_count: int
    ratio: float


class ModeratorWorkload(BaseModel):
    moderator_id: UUID
    display_name: str
    reviews: int


class SystemStatsResponse(BaseModel):
    days: int
    videos_total: int
    videos_by_status: dict[str, int]
    labels: list[LabelStat]
    reports_by_status: dict[str, int]
    appeals_by_status: dict[str, int]
    jobs_by_status: dict[str, int]
    moderator_workload: list[ModeratorWorkload]
