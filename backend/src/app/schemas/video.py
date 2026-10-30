from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import VideoStatus


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    caption: str | None
    size_bytes: int
    status: VideoStatus
    created_at: datetime
    owner_name: str | None = None


class LabelResponse(BaseModel):
    name: str
    confidence: float
    level: str


class AIResultResponse(BaseModel):
    video_id: UUID
    job_status: str
    transcript: str | None
    labels: list[LabelResponse]
