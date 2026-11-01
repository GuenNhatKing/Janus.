from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.dependencies import current_user, optional_user
from app.models import User, Video
from app.schemas import (
    AIResultResponse,
    ConfirmLabelsRequest,
    LabelResponse,
    ReportCreate,
    ReportResponse,
    VideoLabelsResponse,
    VideoResponse,
    VideoUpdate,
)
from app.services import (
    ai_service,
    moderation_service,
    video_label_service,
    video_service,
)

router = APIRouter(tags=["videos"])


@router.post("/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    caption: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Video:
    # Đọc tối đa đúng ngưỡng cho phép để phát hiện file quá lớn mà không nạp cả file vào bộ nhớ.
    settings = get_settings()
    video = video_service.upload_video(
        db,
        owner=user,
        filename=file.filename or "",
        content_type=file.content_type,
        content=file.file.read(settings.max_upload_size_bytes + 1),
        caption=caption,
    )
    if get_settings().ai_analysis_mode.strip().lower() == "off":
        background_tasks.add_task(ai_service.run_mock_analysis, video.id)
    else:
        background_tasks.add_task(ai_service.run_video_analysis, video.id)
    return video


@router.get("/videos", response_model=list[VideoResponse])
def list_my_videos(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Video]:
    return video_service.list_owned_videos(db, user)


@router.get("/feed", response_model=list[VideoResponse])
def feed(db: Session = Depends(get_db)) -> list[Video]:
    return video_service.list_published_feed(db)


@router.get("/videos/{video_id}/ai", response_model=AIResultResponse)
def ai_result(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AIResultResponse:
    return video_service.get_ai_result(db, video_id, user)


@router.patch("/videos/{video_id}", response_model=VideoResponse)
def update_video(
    video_id: UUID,
    payload: VideoUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Video:
    return video_service.update_video(db, video_id, user, payload)


@router.get("/videos/{video_id}/labels", response_model=list[LabelResponse])
def labels(
    video_id: UUID,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
) -> list[LabelResponse]:
    return video_label_service.list_video_labels(db, video_id, user)


@router.post(
    "/videos/{video_id}/labels/confirm",
    response_model=VideoLabelsResponse,
)
def confirm_labels(
    video_id: UUID,
    payload: ConfirmLabelsRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> VideoLabelsResponse:
    return video_label_service.confirm_video_labels(db, video_id, user, payload)


@router.get("/videos/{video_id}/stream")
def stream_video(video_id: UUID, user: User | None = Depends(optional_user), db: Session = Depends(get_db)) -> FileResponse:
    path = video_service.resolve_stream_path(db, video_id, user)
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
        headers={"Cache-Control": "private, max-age=60"},
    )


@router.delete("/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    video_service.soft_delete_video(db, video_id, user)


@router.post("/videos/{video_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    video_id: UUID,
    payload: ReportCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    return moderation_service.create_report(db, video_id, user, payload.reason)
