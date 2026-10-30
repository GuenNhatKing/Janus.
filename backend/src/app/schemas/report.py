from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportStatus


class ReportCreate(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    video_id: UUID
    video_caption: str | None = None
    reason: str
    status: ReportStatus
