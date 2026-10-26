from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class VideoStatus(str, Enum):
    processing = "processing"
    pending_review = "pending_review"
    published = "published"
    rejected = "rejected"
    failed = "failed"
    deleted = "deleted"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class ReportStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    rejected = "rejected"


class AppealStatus(str, Enum):
    open = "open"
    approved = "approved"
    rejected = "rejected"


class ModerationAction(str, Enum):
    approve = "approve"
    reject = "reject"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.user, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    videos: Mapped[list["Video"]] = relationship(back_populates="owner")


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped[Video] = relationship(back_populates="ai_jobs")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped["User"] = relationship()


class RevokedToken(Base):
    """Danh sách access token (jti) đã bị đăng xuất trước khi hết hạn."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Appeal(Base):
    __tablename__ = "appeals"
    # Chỉ cho phép một appeal đang mở cho mỗi (video, user); các appeal cũ đã
    # quyết định vẫn giữ lại làm lịch sử.
    __table_args__ = (
        Index(
            "uq_appeal_open",
            "video_id",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
            sqlite_where=text("status = 'open'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AppealStatus] = mapped_column(SqlEnum(AppealStatus), default=AppealStatus.open, nullable=False, index=True)
    moderator_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    video: Mapped["Video"] = relationship()
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    moderator: Mapped["User"] = relationship(foreign_keys=[moderator_id])


class ModerationReview(Base):
    __tablename__ = "moderation_reviews"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id"), index=True)
    moderator_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[ModerationAction | None] = mapped_column(SqlEnum(ModerationAction), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    video: Mapped[Video] = relationship(back_populates="moderation_reviews")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("video_id", "reporter_id", name="uq_video_reporter"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    video_id: Mapped[UUID] = mapped_column(ForeignKey("videos.id"), index=True)
    reporter_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(SqlEnum(ReportStatus), default=ReportStatus.open)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    video: Mapped[Video] = relationship(back_populates="reports")

