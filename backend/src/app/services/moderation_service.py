"""Nghiệp vụ báo cáo và kiểm duyệt."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import ConflictError, NotFoundError
from app.models import (
    ModerationAction,
    ModerationReview,
    Report,
    ReportStatus,
    User,
    Video,
    VideoStatus,
)


def create_report(db: Session, video_id: UUID, reporter: User, reason: str) -> Report:
    """Người dùng báo cáo video; mỗi người chỉ báo cáo mỗi video một lần (409)."""
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise NotFoundError("Không tìm thấy video")
    existing = db.scalar(
        select(Report).where(
            Report.video_id == video_id,
            Report.reporter_id == reporter.id,
            Report.status == ReportStatus.open,
        )
    )
    if existing is not None:
        raise ConflictError("Bạn đã báo cáo video này")
    report = Report(video_id=video_id, reporter_id=reporter.id, reason=reason)
    if video.status == VideoStatus.published:
        video.status = VideoStatus.pending_review
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def moderation_queue(db: Session) -> list[Video]:
    return list(
        db.scalars(
            select(Video)
            .options(selectinload(Video.owner))
            .where(Video.status == VideoStatus.pending_review, Video.is_deleted.is_(False))
            .order_by(Video.created_at)
        )
    )


def decide_video(db: Session, video_id: UUID, moderator: User, action: ModerationAction, reason: str | None) -> None:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise NotFoundError("Không tìm thấy video")
    video.status = VideoStatus.published if action == ModerationAction.approve else VideoStatus.rejected
    db.add(
        ModerationReview(
            video_id=video.id,
            moderator_id=moderator.id,
            action=action,
            reason=reason,
        )
    )
    db.commit()


def list_open_reports(db: Session) -> list[Report]:
    return list(
        db.scalars(
            select(Report).where(Report.status == ReportStatus.open).order_by(Report.created_at)
        )
    )


def decide_report(db: Session, report_id: UUID, moderator: User, action: ModerationAction, reason: str | None) -> None:
    """Quyết định báo cáo: approve = video vi phạm (ẩn video), reject = bỏ báo cáo."""
    report = db.get(Report, report_id)
    if report is None or report.status != ReportStatus.open:
        raise NotFoundError("Không tìm thấy báo cáo đang chờ xử lý")
    video = db.get(Video, report.video_id)
    if video is None:
        raise NotFoundError("Không tìm thấy video liên quan")
    report.status = ReportStatus.resolved if action == ModerationAction.reject else ReportStatus.rejected
    video.status = VideoStatus.rejected if action == ModerationAction.approve else VideoStatus.published
    db.add(
        ModerationReview(
            video_id=video.id,
            moderator_id=moderator.id,
            action=action,
            reason=reason,
        )
    )
    db.commit()
