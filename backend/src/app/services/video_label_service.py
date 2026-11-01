"""Nghiệp vụ xem và xác nhận nhãn video."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import ForbiddenError, NotFoundError
from app.models import (
    AIJob,
    JobStatus,
    Label,
    LabelSource,
    User,
    UserRole,
    Video,
    VideoLabel,
    VideoStatus,
    VideoVisibility,
)
from app.schemas import (
    ConfirmLabelsRequest,
    LabelResponse,
    VideoLabelsResponse,
)


def _get_video(db: Session, video_id: UUID) -> Video:
    video = db.scalar(
        select(Video)
        .options(selectinload(Video.owner), selectinload(Video.labels).selectinload(VideoLabel.label))
        .where(Video.id == video_id, Video.is_deleted.is_(False))
    )
    if video is None:
        raise NotFoundError("Không tìm thấy video")
    return video


def _can_view(video: Video, requester: User | None) -> bool:
    if (
        video.status == VideoStatus.published
        and video.visibility == VideoVisibility.public
    ):
        return True
    return requester is not None and (
        requester.id == video.owner_id
        or requester.role in {UserRole.moderator, UserRole.admin}
    )


def _label_response(video: Video) -> list[LabelResponse]:
    return [
        LabelResponse(
            name=item.label.name,
            confidence=item.confidence,
            level=item.level,
            source=item.source,
        )
        for item in video.labels
    ]


def list_video_labels(
    db: Session, video_id: UUID, requester: User | None
) -> list[LabelResponse]:
    video = _get_video(db, video_id)
    if not _can_view(video, requester):
        raise NotFoundError("Không tìm thấy video")
    return _label_response(video)


def confirm_video_labels(
    db: Session,
    video_id: UUID,
    owner: User,
    payload: ConfirmLabelsRequest,
) -> VideoLabelsResponse:
    video = _get_video(db, video_id)
    if video.owner_id != owner.id:
        raise ForbiddenError("Bạn không có quyền xác nhận nhãn video này")

    ai_labels = [
        item
        for item in video.labels
        if item.source == LabelSource.ai
    ]
    has_high_risk = any(item.level.upper() == "HIGH" for item in ai_labels)

    db.execute(
        delete(VideoLabel).where(
            VideoLabel.video_id == video_id,
            VideoLabel.source == LabelSource.user,
        )
    )
    for name in payload.labels:
        label = db.scalar(select(Label).where(Label.name.ilike(name)))
        if label is None:
            label = Label(name=name)
            db.add(label)
            db.flush()
        if db.scalar(
            select(VideoLabel.id).where(
                VideoLabel.video_id == video.id,
                VideoLabel.label_id == label.id,
            )
        ):
            continue
        db.add(
            VideoLabel(
                video_id=video.id,
                label_id=label.id,
                confidence=1.0,
                level="LOW",
                source=LabelSource.user,
            )
        )

    job = db.scalar(
        select(AIJob)
        .where(AIJob.video_id == video.id)
        .order_by(AIJob.created_at.desc())
    )
    moderation_required = has_high_risk
    if has_high_risk:
        video.status = VideoStatus.pending_review
    elif (
        job is not None
        and job.status == JobStatus.succeeded
        and video.status != VideoStatus.rejected
    ):
        video.status = VideoStatus.published

    db.commit()
    db.refresh(video)
    video = _get_video(db, video_id)
    return VideoLabelsResponse(
        video=video,
        labels=_label_response(video),
        moderation_required=moderation_required,
    )
