from pathlib import Path
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.dependencies import current_user, require_roles
from app.models import AIJob, Label, ModerationAction, ModerationReview, Report, ReportStatus, User, UserRole, Video, VideoStatus
from app.schemas import (
    AIResultResponse,
    AdminRoleUpdate,
    AdminUserDetail,
    AdminUserStatusUpdate,
    AdminUserSummary,
    LoginRequest,
    ModerationDecisionRequest,
    ReportCreate,
    ReportResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    VideoResponse,
)
from app.security import create_access_token, hash_password, verify_password
from app.services import run_mock_analysis, validate_mp4_content

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
def create_storage() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="Email đã được sử dụng")
    user = User(email=payload.email.lower(), display_name=payload.display_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác")
    return TokenResponse(access_token=create_access_token(user))


@app.get("/api/v1/profile", response_model=UserResponse)
def profile(user: User = Depends(current_user)) -> User:
    return user


@app.get("/api/v1/admin/users", response_model=list[AdminUserSummary])
def admin_list_users(
    search: str | None = None,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    query = select(User).order_by(User.created_at.desc())
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(User.display_name.ilike(pattern) | User.email.ilike(pattern))
    return list(db.scalars(query))


@app.get("/api/v1/admin/users/{user_id}", response_model=AdminUserDetail)
def admin_get_user(
    user_id: UUID,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    return target


@app.patch("/api/v1/admin/users/{user_id}/status", response_model=AdminUserDetail)
def admin_update_user_status(
    user_id: UUID,
    payload: AdminUserStatusUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if target.id == user.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản admin hiện tại")
    target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return target


@app.get("/api/v1/admin/moderators", response_model=list[AdminUserSummary])
def admin_list_moderators(
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role.in_((UserRole.moderator, UserRole.admin)))
            .order_by(User.created_at.desc())
        )
    )


@app.patch("/api/v1/admin/users/{user_id}/role", response_model=AdminUserDetail)
def admin_update_user_role(
    user_id: UUID,
    payload: AdminRoleUpdate,
    user: User = Depends(require_roles(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    if target.id == user.id and payload.role != UserRole.admin:
        raise HTTPException(status_code=400, detail="Không thể tự thu hồi quyền admin hiện tại")
    target.role = payload.role
    db.commit()
    db.refresh(target)
    return target


@app.post("/api/v1/videos", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    caption: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Video:
    filename = file.filename or ""
    if Path(filename).suffix.lower() != settings.allowed_video_extension or file.content_type != "video/mp4":
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận tệp MP4")
    content = file.file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=413, detail="Video vượt quá dung lượng 50MB")
    try:
        validate_mp4_content(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    video = Video(
        owner_id=user.id,
        original_filename=Path(filename).name,
        storage_path="",
        mime_type="video/mp4",
        size_bytes=len(content),
        caption=caption,
    )
    db.add(video)
    db.flush()
    path = Path(settings.upload_dir) / f"{video.id}.mp4"
    path.write_bytes(content)
    video.storage_path = str(path)
    job = AIJob(video_id=video.id)
    db.add(job)
    db.commit()
    db.refresh(video)
    background_tasks.add_task(run_mock_analysis, video.id)
    return video


@app.get("/api/v1/videos", response_model=list[VideoResponse])
def list_my_videos(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.owner_id == user.id, Video.is_deleted.is_(False)).order_by(Video.created_at.desc())))


@app.get("/api/v1/feed", response_model=list[VideoResponse])
def feed(db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.status == VideoStatus.published, Video.is_deleted.is_(False)).order_by(Video.created_at.desc()).limit(50)))


@app.get("/api/v1/videos/{video_id}/ai", response_model=AIResultResponse)
def ai_result(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> AIResultResponse:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted or (video.owner_id != user.id and user.role not in {UserRole.moderator, UserRole.admin}):
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    job = db.scalar(select(AIJob).where(AIJob.video_id == video_id).order_by(AIJob.created_at.desc()))
    labels = [
        {"name": item.label.name, "confidence": item.confidence, "level": item.level}
        for item in video.labels
    ]
    return AIResultResponse(video_id=video_id, job_status=job.status.value if job else "unknown", transcript=job.transcript if job else None, labels=labels)


@app.delete("/api/v1/videos/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    video = db.get(Video, video_id)
    if video is None or video.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    video.is_deleted = True
    video.status = VideoStatus.deleted
    db.commit()


@app.post("/api/v1/videos/{video_id}/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(video_id: UUID, payload: ReportCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Report:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if db.scalar(select(Report).where(Report.video_id == video_id, Report.reporter_id == user.id, Report.status == ReportStatus.open)):
        raise HTTPException(status_code=409, detail="Bạn đã báo cáo video này")
    report = Report(video_id=video_id, reporter_id=user.id, reason=payload.reason)
    if video.status == VideoStatus.published:
        video.status = VideoStatus.pending_review
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@app.get("/api/v1/moderation/queue", response_model=list[VideoResponse])
def moderation_queue(user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)), db: Session = Depends(get_db)) -> list[Video]:
    return list(db.scalars(select(Video).where(Video.status == VideoStatus.pending_review, Video.is_deleted.is_(False)).order_by(Video.created_at)))


@app.post("/api/v1/moderation/videos/{video_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def moderation_decision(
    video_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    video = db.get(Video, video_id)
    if video is None or video.is_deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy video")
    if payload.action == ModerationAction.approve:
        video.status = VideoStatus.published
    else:
        video.status = VideoStatus.rejected
    db.add(ModerationReview(video_id=video.id, moderator_id=user.id, action=payload.action, reason=payload.reason))
    db.commit()


@app.get("/api/v1/moderation/reports", response_model=list[ReportResponse])
def moderation_reports(
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[Report]:
    return list(db.scalars(select(Report).where(Report.status == ReportStatus.open).order_by(Report.created_at)))


@app.post("/api/v1/moderation/reports/{report_id}/decision", status_code=status.HTTP_204_NO_CONTENT)
def report_decision(
    report_id: UUID,
    payload: ModerationDecisionRequest,
    user: User = Depends(require_roles(UserRole.moderator, UserRole.admin)),
    db: Session = Depends(get_db),
) -> None:
    report = db.get(Report, report_id)
    if report is None or report.status != ReportStatus.open:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo cáo đang chờ xử lý")
    video = db.get(Video, report.video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy video liên quan")
    report.status = ReportStatus.resolved if payload.action == ModerationAction.reject else ReportStatus.rejected
    if payload.action == ModerationAction.approve:
        video.status = VideoStatus.rejected
    else:
        video.status = VideoStatus.published
    db.add(ModerationReview(video_id=video.id, moderator_id=user.id, action=payload.action, reason=payload.reason))
    db.commit()
