from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
from app.models.enums import ModerationAction, ReportStatus
from app.models.video import Video


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

    @property
    def video_caption(self) -> str | None:
        """Mô tả (hoặc tên tệp) của video bị báo cáo, để moderator nhận ra video trong hàng đợi."""
        if self.video is None:
            return None
        return self.video.caption or self.video.original_filename
