from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
from app.models.enums import JobStatus, VideoStatus
from app.models.user import User


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VideoStatus] = mapped_column(SqlEnum(VideoStatus), default=VideoStatus.processing, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    owner: Mapped[User] = relationship(back_populates="videos")
    ai_jobs: Mapped[list["AIJob"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    labels: Mapped[list["VideoLabel"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="video")
    moderation_reviews: Mapped[list["ModerationReview"]] = relationship(back_populates="video")

    @property
    def owner_name(self) -> str:
        """Tên hiển thị của chủ video, dùng cho response pública (feed, hàng đợi kiểm duyệt)."""
        return self.owner.display_name


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    videos: Mapped[list["VideoLabel"]] = relationship(back_populates="label")


class VideoLabel(Base):
    __tablename__ = "video_labels"
    __table_args__ = (UniqueConstraint("video_id", "label_id", name="uq_video_label"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id"), index=True)
    label_id: Mapped[UUID] = mapped_column(ForeignKey("labels.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    level: Mapped[str] = mapped_column(String(10))

    video: Mapped[Video] = relationship(back_populates="labels")
    label: Mapped[Label] = relationship(back_populates="videos")


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id"), index=True)
    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus), default=JobStatus.pending)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped[Video] = relationship(back_populates="ai_jobs")
